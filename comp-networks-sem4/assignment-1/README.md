# HTTP Proxy Server

A simple HTTP proxy server built using C sockets for my Computer Networks course (Semester 4).

## What It Does

This proxy server sits between a client and a web server. It:
- Accepts HTTP requests from clients
- Forwards them to the target web server
- Sends the response back to the client

## Features

- **HTTP GET Support** - Handles GET requests only (other methods return 501 Not Implemented)
- **HTTP Version Check** - Supports HTTP/1.0 and HTTP/1.1
- **Header Validation** - Validates that request headers are properly formatted
- **Multi-client Support** - Uses `fork()` to handle multiple clients simultaneously
- **Error Handling** - Returns 400 Bad Request for invalid requests
- **Custom Port** - You can run the proxy on any available port

## How to Compile

```bash
gcc -o proxy proxy.c
```

## How to Run

```bash
./proxy <port_number>
```

Example:
```bash
./proxy 8080
```

## How It Works

1. Client sends an HTTP request to the proxy
2. Proxy validates the request (method, version, headers)
3. Proxy parses the URL to extract host, port, and path
4. Proxy connects to the target server
5. Proxy forwards the request and relays the response back to the client

## Limitations

- Only supports GET method
- No caching
- No HTTPS support
- Basic error handling

---
**Course:** Computer Networks | **Semester:** 4 | **Assignment:** 1
