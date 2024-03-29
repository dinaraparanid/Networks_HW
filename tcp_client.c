#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <zconf.h>

#define SERVER_IP_ADDR "158.160.145.207"
#define SERVER_PORT 2001
#define MAX_BUF 128

int main() {
    const int sockfd = socket(AF_INET, SOCK_STREAM, 0);

    if (sockfd < 0) {
        perror("socket");
        exit(EXIT_FAILURE);
    }

    struct sockaddr_in servaddr;

    memset(&servaddr, 0, sizeof(servaddr));

    servaddr.sin_family = AF_INET;
    servaddr.sin_port = htons(SERVER_PORT);
    servaddr.sin_addr.s_addr = inet_addr(SERVER_IP_ADDR);

    char req_buf[MAX_BUF];
    char res_buf[MAX_BUF];

    if (connect(sockfd, (struct sockaddr*)&servaddr, sizeof(servaddr)) < 0) {
        perror("connect");
        exit(EXIT_FAILURE);
    }

    memset(req_buf, 0, MAX_BUF);
    sprintf(req_buf, "Arseny Savchenko");
    send(sockfd, req_buf, strlen(req_buf), 0);

    FILE* create = fopen("image.svg", "w");
    fclose(create);

    FILE* image = fopen("image.svg", "a");

    for (;;) {
        const ssize_t size = recv(sockfd, res_buf, MAX_BUF, 0);
        printf("SIZE: %d\n", size);

        if (size <= 0)
            break;

        res_buf[size] = '\0';
        fwrite(res_buf, sizeof res_buf[0], size, image);
    }

    fclose(image);
    close(sockfd);
    return EXIT_SUCCESS;
}
