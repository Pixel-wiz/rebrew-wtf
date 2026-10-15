/* second binary for the multi-binary test: distinct self-contained functions */
int lib_add(int a, int b) { return a + b; }
int lib_max3(int a, int b, int c) {
    int m = a > b ? a : b;
    return m > c ? m : c;
}
unsigned lib_mix(unsigned x) {
    x ^= x >> 16; x *= 0x7feb352du; x ^= x >> 15;
    return x;
}
int main(void) { return lib_add(lib_max3(1,2,3), (int)lib_mix(7)); }
