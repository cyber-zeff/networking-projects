#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <netinet/in.h>
#include <signal.h>
#include <sys/wait.h>

#define BUFFER_SIZE 8192
#define MAX_PROCESSES 100
int active_processes = 0;

void send_400(int client_socket)
{
    char *response =
        "HTTP/1.0 400 Bad Request\r\n"
        "Content-Type: text/plain\r\n"
        "\r\n"
        "400 Bad Request\n";
    send(client_socket, response, strlen(response), 0);
}

void send_501(int client_socket)
{
    char *response =
        "HTTP/1.0 501 Not Implemented\r\n"
        "Content-Type: text/plain\r\n"
        "\r\n"
        "501 Not Implemented\n";
    send(client_socket, response, strlen(response), 0);
}

int validate_headers(char *buffer)
{
    char *header_start = strstr(buffer, "\r\n");
    if (!header_start)
        return 0; // No headers at all

    header_start += 2; // Move past first \r\n (request line)
    char *header_end = strstr(header_start, "\r\n\r\n");
    if (!header_end)
        return 0;

    char *line = header_start;
    while (line < header_end)
    {
        char *next = strstr(line, "\r\n");
        if (!next || next > header_end)
            break;

        char *colon = memchr(line, ':', next - line);
        if (!colon)
            return 0;

        line = next + 2;
    }
    return 1;
}

void handle_client(int client_socket)
{

    char buffer[BUFFER_SIZE];
    memset(buffer, 0, BUFFER_SIZE);

    int bytes = recv(client_socket, buffer, BUFFER_SIZE - 1, 0);
    if (bytes <= 0)
    {
        close(client_socket);
        return;
    }

    // ---- STEP 1: Parse Request Line ----
    char method[16], url[2048], version[16];

    if (sscanf(buffer, "%s %s %s", method, url, version) != 3)
    {
        send_400(client_socket);
        close(client_socket);
        return;
    }

    if (!validate_headers(buffer))
    {
        send_400(client_socket);
        close(client_socket);
        return;
    }

    // ---- STEP 2: Check Method ----
    if (strcmp(method, "GET") != 0)
    {
        send_501(client_socket);
        close(client_socket);
        return;
    }

    // ---- STEP 3: Check HTTP Version ----
    if (strcmp(version, "HTTP/1.0") != 0 && strcmp(version, "HTTP/1.1") != 0)
    {
        send_400(client_socket);
        close(client_socket);
        return;
    }

    // ---- STEP 4: Parse URL ----
    char host[512], path[2048];
    int port = 80;

    if (strncmp(url, "http://", 7) != 0)
    {
        send_400(client_socket);
        close(client_socket);
        return;
    }

    char *url_ptr = url + 7;
    char *slash = strchr(url_ptr, '/');

    if (slash)
    {
        strcpy(path, slash);
        *slash = '\0';
    }
    else
    {
        strcpy(path, "/");
    }

    char *colon = strchr(url_ptr, ':');
    if (colon)
    {
        *colon = '\0';
        strcpy(host, url_ptr);
        port = atoi(colon + 1);
    }
    else
    {
        strcpy(host, url_ptr);
    }

    // ---- DEBUG PRINTS ----
    printf("====================================\n");
    printf("Request from client:\n%s\n", buffer);
    printf("Forwarding to host: %s\n", host);
    printf("Port: %d\n", port);
    printf("Path: %s\n", path);
    printf("====================================\n\n");

    // ---- STEP 5: Connect to Remote Server ----
    int server_socket = socket(AF_INET, SOCK_STREAM, 0);
    if (server_socket < 0)
    {
        close(client_socket);
        return;
    }

    struct hostent *server = gethostbyname(host);
    if (server == NULL)
    {
        send_400(client_socket);
        close(server_socket);
        close(client_socket);
        return;
    }

    struct sockaddr_in server_addr;
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(port);
    memcpy(&server_addr.sin_addr.s_addr,
           server->h_addr,
           server->h_length);

    if (connect(server_socket,
                (struct sockaddr *)&server_addr,
                sizeof(server_addr)) < 0)
    {
        close(server_socket);
        close(client_socket);
        return;
    }

    // ---- STEP 6: Forward Modified Request ----
    char request[BUFFER_SIZE];
    snprintf(request, sizeof(request),
             "GET %s HTTP/1.0\r\n"
             "Host: %s\r\n"
             "\r\n",
             path, host);

    send(server_socket, request, strlen(request), 0);

    // ---- STEP 7: Relay Response ----
    while ((bytes = recv(server_socket, buffer, BUFFER_SIZE, 0)) > 0)
    {
        send(client_socket, buffer, bytes, 0);
    }

    close(server_socket);
    close(client_socket);
}

void reap_zombie(int sig)
{
    while (waitpid(-1, NULL, WNOHANG) > 0)
    {
        active_processes--;
    }
}

int main(int argc, char *argv[])
{

    if (argc != 2)
    {
        printf("Usage: %s <port>\n", argv[0]);
        return 1;
    }

    int port = atoi(argv[1]);

    int proxy_socket = socket(AF_INET, SOCK_STREAM, 0);
    if (proxy_socket < 0)
    {
        perror("socket failed");
        return 1;
    }

    int opt = 1;
    setsockopt(proxy_socket, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    addr.sin_addr.s_addr = INADDR_ANY;

    if (bind(proxy_socket, (struct sockaddr *)&addr, sizeof(addr)) < 0)
    {
        perror("bind failed");
        return 1;
    }

    if (listen(proxy_socket, 10) < 0)
    {
        perror("listen failed");
        return 1;
    }

    printf("Proxy running on port %d...\n", port);

    signal(SIGCHLD, reap_zombie);
    while (1)
    {
        struct sockaddr_in client_addr;
        socklen_t len = sizeof(client_addr);

        int client_socket =
            accept(proxy_socket,
                   (struct sockaddr *)&client_addr,
                   &len);

        if (active_processes >= MAX_PROCESSES)
        {
            printf("Maximum processes reached.\n");
            close(client_socket);
            continue;
        }

        pid_t pid = fork();

        if (pid == 0)
        {
            close(proxy_socket);
            handle_client(client_socket);
            exit(0);
        }
        else if (pid > 0)
        {
            active_processes++;
        }
        else
        {
            perror("fork failed");
        }

        close(client_socket);
    }

    close(proxy_socket);
    return 0;
}