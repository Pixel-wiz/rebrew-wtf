/* Known-answer test target for rebrew-wtf: small, varied functions compiled with gcc 14.2 -O2. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct Node {
    int key;
    int value;
    struct Node *next;
} Node;

static unsigned int g_seed = 12345;
int g_counter;
char g_buffer[64];

unsigned int toy_rand(void) {
    g_seed = g_seed * 1103515245u + 12345u;
    return (g_seed >> 16) & 0x7fff;
}

int toy_clamp(int v, int lo, int hi) {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

unsigned int toy_adler32(const unsigned char *data, size_t len) {
    unsigned int a = 1, b = 0;
    for (size_t i = 0; i < len; i++) {
        a = (a + data[i]) % 65521;
        b = (b + a) % 65521;
    }
    return (b << 16) | a;
}

int toy_count_char(const char *s, char c) {
    int n = 0;
    while (*s) {
        if (*s++ == c) n++;
    }
    return n;
}

void toy_reverse(char *s) {
    size_t n = strlen(s);
    for (size_t i = 0; i < n / 2; i++) {
        char t = s[i];
        s[i] = s[n - 1 - i];
        s[n - 1 - i] = t;
    }
}

Node *toy_push(Node *head, int key, int value) {
    Node *n = malloc(sizeof(Node));
    if (!n) return head;
    n->key = key;
    n->value = value;
    n->next = head;
    g_counter++;
    return n;
}

int toy_find(const Node *head, int key, int fallback) {
    for (; head; head = head->next) {
        if (head->key == key) return head->value;
    }
    return fallback;
}

void toy_free(Node *head) {
    while (head) {
        Node *next = head->next;
        free(head);
        g_counter--;
        head = next;
    }
}

int toy_state(int state, char input) {
    switch (state) {
    case 0: return input == 'a' ? 1 : 0;
    case 1: return input == 'b' ? 2 : (input == 'a' ? 1 : 0);
    case 2: return input == 'c' ? 3 : 0;
    case 3: return 3;
    default: return -1;
    }
}

int toy_matches(const char *s) {
    int st = 0;
    while (*s && st != 3) st = toy_state(st, *s++);
    return st == 3;
}

double toy_mean(const int *v, int n) {
    if (n <= 0) return 0.0;
    long long sum = 0;
    for (int i = 0; i < n; i++) sum += v[i];
    return (double)sum / n;
}

void toy_format(int id, const char *name) {
    snprintf(g_buffer, sizeof g_buffer, "[%04d] %s", id, name);
}

int toy_parse_hex(const char *s) {
    int v = 0;
    for (; *s; s++) {
        int d;
        if (*s >= '0' && *s <= '9') d = *s - '0';
        else if (*s >= 'a' && *s <= 'f') d = *s - 'a' + 10;
        else if (*s >= 'A' && *s <= 'F') d = *s - 'A' + 10;
        else return -1;
        v = v * 16 + d;
    }
    return v;
}

int main(int argc, char **argv) {
    Node *list = NULL;
    for (int i = 0; i < 8; i++) list = toy_push(list, i, (int)toy_rand());
    printf("%d %d\n", toy_find(list, 3, -1), toy_clamp(argc * 100, 0, 255));
    char word[] = "abcabc";
    toy_reverse(word);
    printf("%s %d %u\n", word, toy_count_char(word, 'a'), toy_adler32((const unsigned char *)word, strlen(word)));
    printf("%d %d\n", toy_matches(argc > 1 ? argv[1] : "xxabcx"), toy_parse_hex("1f"));
    int nums[] = {1, 2, 3, 4};
    printf("%.2f\n", toy_mean(nums, 4));
    toy_format(7, "toy");
    puts(g_buffer);
    toy_free(list);
    return g_counter;
}
