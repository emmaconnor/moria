#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_USERNAME_LEN 32

struct user
{
    int id;
    char name[MAX_USERNAME_LEN];
    void *void_ptr;
    struct user *prev;
    struct user *next;
};

int getline_with_prompt(char *prompt, char **line, size_t *linecap)
{
    printf("%s", prompt);
    fflush(stdout);
    return getline(line, linecap, stdin);
}

int main(int argc, char **argv)
{
    int next_id = 0;

    char *line = NULL;
    size_t line_size = 0;

    struct user list_head;
    list_head.next = &list_head;
    list_head.prev = &list_head;

    struct user *user;
    while (getline_with_prompt("username: ", &line, &line_size) > 0)
    {
        size_t len = strnlen(line, line_size);
        while (len > 0 && line[len - 1] == '\n')
        {
            line[--len] = '\0';
        }

        user = malloc(sizeof(user));

        user->id = next_id++;
        snprintf(user->name, MAX_USERNAME_LEN, "%s", line);

        user->prev = list_head.prev;
        list_head.prev->next = user;

        user->next = &list_head;
        list_head.prev = user;

        printf("created user with id %d\n", user->id);
    }

    puts("");
    user = &list_head;
    while (user->next != &list_head)
    {
        user = user->next;
        printf("user %d: %s\n", user->id, user->name);
    }

    return 0;
}
