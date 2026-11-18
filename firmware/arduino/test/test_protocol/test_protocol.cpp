// Host-side tests for the serial protocol:  pio test -e native
#include <initializer_list>
#include <math.h>
#include <string.h>
#include <unity.h>

#include "ecrt_protocol.h"

using namespace ecrt;

void setUp() {}
void tearDown() {}

static void expectFixed(float v, uint8_t d, const char* want) {
  char b[16];
  formatFixed(b, sizeof b, v, d);
  TEST_ASSERT_EQUAL_STRING(want, b);
}

void test_fixed() {
  expectFixed(230.1f, 1, "230.1");
  expectFixed(1.234f, 3, "1.234");
  expectFixed(12.345f, 3, "12.345");
  expectFixed(0.98f, 2, "0.98");
  expectFixed(0.0f, 3, "0.000");
  expectFixed(0.05f, 1, "0.1");     // rounds half up
  expectFixed(-3.25f, 1, "-3.3");
  expectFixed(-0.01f, 1, "0.0");    // no "-0.0"
  expectFixed(9999.999f, 3, "9999.999");
  expectFixed(7.0f, 0, "7");
}

void test_fixed_rejects() {
  char b[16];
  TEST_ASSERT_EQUAL(0, formatFixed(b, sizeof b, NAN, 1));
  TEST_ASSERT_EQUAL_STRING("", b);
  TEST_ASSERT_EQUAL(0, formatFixed(b, sizeof b, INFINITY, 1));
  char tiny[4];
  TEST_ASSERT_EQUAL(0, formatFixed(tiny, sizeof tiny, 123.45f, 2));
}

void test_line_valid() {
  Measurement m;
  m.valid = true;
  m.volts = 230.1f; m.amps = 1.234f; m.watts = 283.9f; m.kwh = 12.345f; m.hz = 50.0f; m.pf = 0.98f;
  const bool r[4] = {false, true, false, false};
  char b[64];
  size_t n = formatLine(b, sizeof b, m, r);
  TEST_ASSERT_EQUAL_STRING("230.1,1.234,283.9,12.345,50.0,0.98,0,1,0,0\n", b);
  TEST_ASSERT_EQUAL(strlen(b), n);
}

void test_line_no_reply() {
  Measurement m;  // valid = false
  const bool r[4] = {false, true, false, false};
  char b[64];
  formatLine(b, sizeof b, m, r);
  TEST_ASSERT_EQUAL_STRING(",,,,,,0,1,0,0\n", b);
}

void test_line_too_small() {
  Measurement m;
  m.valid = true;
  const bool r[4] = {false, false, false, false};
  char b[20];
  TEST_ASSERT_EQUAL(0, formatLine(b, sizeof b, m, r));
}

void test_command() {
  uint8_t ch = 9;
  bool on = false;
  TEST_ASSERT_TRUE(parseCommand("R,2,1", ch, on));
  TEST_ASSERT_EQUAL(1, ch);
  TEST_ASSERT_TRUE(on);
  TEST_ASSERT_TRUE(parseCommand("R,4,0", ch, on));
  TEST_ASSERT_EQUAL(3, ch);
  TEST_ASSERT_FALSE(on);
}

void test_command_rejects() {
  uint8_t ch;
  bool on;
  for (const char* bad : {"", "R", "R,0,1", "R,5,1", "R,1,2", "R,1,1,", "r,1,1", "R,10,1", "R,1", "X,1,1", "R,1,"})
    TEST_ASSERT_FALSE_MESSAGE(parseCommand(bad, ch, on), bad);
}

static int feedAll(LineReader& lr, const char* s, char out[][24], int max) {
  int n = 0;
  for (; *s; s++)
    if (lr.feed(*s) && n < max) strcpy(out[n++], lr.line());
  return n;
}

void test_reader() {
  LineReader lr;
  char got[4][24];
  int n = feedAll(lr, "R,1,1\r\nR,2,0\n\n\nR,3,1\n", got, 4);
  TEST_ASSERT_EQUAL(3, n);
  TEST_ASSERT_EQUAL_STRING("R,1,1", got[0]);
  TEST_ASSERT_EQUAL_STRING("R,2,0", got[1]);
  TEST_ASSERT_EQUAL_STRING("R,3,1", got[2]);
}

void test_reader_overflow() {
  LineReader lr;
  char got[4][24];
  int n = feedAll(lr, "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\nR,1,1\n", got, 4);
  TEST_ASSERT_EQUAL(1, n);
  TEST_ASSERT_EQUAL_STRING("R,1,1", got[0]);
  TEST_ASSERT_EQUAL(1, lr.dropped());
}

void test_reader_partial() {
  LineReader lr;
  char got[2][24];
  TEST_ASSERT_EQUAL(0, feedAll(lr, "R,1", got, 2));
  TEST_ASSERT_EQUAL(1, feedAll(lr, ",1\n", got, 2));
  TEST_ASSERT_EQUAL_STRING("R,1,1", got[0]);
}

int main() {
  UNITY_BEGIN();
  RUN_TEST(test_fixed);
  RUN_TEST(test_fixed_rejects);
  RUN_TEST(test_line_valid);
  RUN_TEST(test_line_no_reply);
  RUN_TEST(test_line_too_small);
  RUN_TEST(test_command);
  RUN_TEST(test_command_rejects);
  RUN_TEST(test_reader);
  RUN_TEST(test_reader_overflow);
  RUN_TEST(test_reader_partial);
  return UNITY_END();
}
