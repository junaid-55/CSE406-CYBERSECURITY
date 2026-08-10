#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// ============================================================
// IMPORTANT: Replace <LAST_3_DIGITS_OF_YOUR_ID> below with
// the last 3 digits of your Student ID without leading zeroes.
// For example, if your ID is 2105067, use 67
// ============================================================
#define STUDENT_ID 6

#define BUF_SZ (100 + STUDENT_ID)
#define READ_SZ (BUF_SZ + 300)

int process(char *str) {
  char buffer[BUF_SZ];

  strcpy(buffer, str);

  return 1;
}

int main(int argc, char **argv) {
  char str[READ_SZ];
  FILE *badfile;

  badfile = fopen("badfile", "r");
  if (!badfile) {
    printf("Error: Cannot open badfile\n");
    return 1;
  }

  fread(str, sizeof(char), READ_SZ, badfile);
  process(str);

  printf("Returned Properly\n");
  return 0;
}
