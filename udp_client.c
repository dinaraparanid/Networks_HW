#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <arpa/inet.h>

#define SERVER_IP_ADDR "127.0.0.1"
#define SERVER_PORT 2000
#define MAX_BUF 128

#define MIN_BORDER 0
#define MAX_BORDER 42

#define MORE "MORE"
#define LESS "LESS"
#define WIN "WIN"
#define LOSE "LOSE"

int main() {
    const int sockfd = socket(AF_INET, SOCK_DGRAM, 0);

    if (sockfd < 0) {
        perror("socket");
        exit(EXIT_FAILURE);
    }

    struct sockaddr_in servaddr;

    memset(&servaddr, 0, sizeof(servaddr));

    servaddr.sin_family = AF_INET;
    servaddr.sin_port = htons(SERVER_PORT);
    servaddr.sin_addr.s_addr = inet_addr(SERVER_IP_ADDR);

    int start = MIN_BORDER;
    int end = MAX_BORDER;

    char req_buf[MAX_BUF];
    char res_buf[MAX_BUF];

    for (;;) {
        const int mid = start + end >> 1;
        memset(req_buf, 0, MAX_BUF);
        sprintf(req_buf, "%d", mid);

        sendto(sockfd, req_buf, strlen(req_buf), MSG_CONFIRM, (const struct sockaddr *) &servaddr, sizeof(servaddr));
        printf("SENDING %d\n", mid);

        socklen_t len;
        const ssize_t size = recvfrom(sockfd, res_buf, MAX_BUF, MSG_WAITALL, (struct sockaddr *) &servaddr,&len);

        res_buf[size] = '\0';

        if (strcmp(res_buf, LESS) == 0) {
            start = mid + 1;
        } else if (strcmp(res_buf, MORE) == 0) {
            end = mid - 1;
        } else if (strcmp(res_buf, LOSE) == 0) {
            printf("I HAVE LOST");
            return 0;
        } else if (strcmp(res_buf, WIN) == 0) {
            printf("I HAVE WON");
            return 0;
        }
    }
}
