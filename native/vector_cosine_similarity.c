#include <math.h>
#include <string.h>
#include <sqlite3ext.h>
#include <stdlib.h>
#include <stdio.h>
#include <ctype.h>
SQLITE_EXTENSION_INIT1

typedef struct {
  int ndims;
  double dims[];
} vector_t;

static vector_t *parse_vector(sqlite3_context *ctx, const char *text)
{
  vector_t *v;
  const char *p = text + 1;
  char *end;
  int i;

  int ndims = 0;
  while (*p) {
    if (*p == ',') {
      ndims++;
    }
    p++;
  }

  ndims++;

  // 不正な入力が渡された場合にはエラーを出す
  if (ndims <= 1) {
    sqlite3_result_error(ctx, "invalid vector, at least 1 dimension is required.", -1);
    return NULL;
  }

  v = malloc(sizeof(vector_t) + sizeof(double) * ndims);
  v->ndims = ndims;

  p = text + 1;
  for (i = 0; i < v->ndims; i++) {
    v->dims[i] = strtod(p, &end);

    // 不正な文字列が含まれている場合
    if (p == end) {
      free(v);
      sqlite3_result_error(ctx, "invalid character in vector literal found.", -1);
      return NULL;
    }

    p = end;
    while (isspace(*p)) {
      p++; // カンマの後にある空白文字をスキップする
    }

    if (*p == ']') {
      if (i != v->ndims - 1) {
        free(v);
        sqlite3_result_error(ctx, "unexpected character ']' in vector literal found.", -1);
        return NULL;
      }
      break;
    }

    if (*p == ',' && i == v->ndims - 1) {
      free(v);
      sqlite3_result_error(ctx, "unexpected comma in vector literal found.", -1);
      return NULL;
    }
    else if (*p != '\0' && *p != ',') {
      free(v);
      sqlite3_result_error(ctx, "unexpected EOS in vector literal found.", -1);
      return NULL;
    }
    if (*p == ',') {
      p++; // カンマをスキップする
    }
  }

  return v;
}

static double cosine_similarity(sqlite3_context *ctx, const vector_t *v1, const vector_t *v2)
{
  double dot_product = 0.0;
  double norm1 = 0.0;
  double norm2 = 0.0;
  int i;

  if (v1->ndims != v2->ndims)
  {
    sqlite3_result_error(ctx, "dimensions of given vectors differ.", -1);
    return NAN;
  }

  for (i = 0; i < v1->ndims; i++) {
    dot_product += v1->dims[i] * v2->dims[i];
    norm1 += v1->dims[i] * v1->dims[i];
    norm2 += v2->dims[i] * v2->dims[i];
  }

  norm1 = sqrt(norm1);
  norm2 = sqrt(norm2);

  if (norm1 == 0.0 || norm2 == 0.0) {
    return 0.0;
  }

  return dot_product / (norm1 * norm2);
}

static void vector_cosine_similarity(sqlite3_context *ctx, int argc, sqlite3_value **argv) {
  const char *text1 = (const char *)sqlite3_value_text(argv[0]);
  const char *text2 = (const char *)sqlite3_value_text(argv[1]);
  vector_t *v1 = parse_vector(ctx, text1);
  vector_t *v2 = parse_vector(ctx, text2);

  if (v1 == NULL || v2 == NULL) {
    return;
  }

  double similarity = cosine_similarity(ctx, v1, v2);

  if (isnan(similarity)) {
    return;
  }

  free(v1);
  free(v2);
  sqlite3_result_double(ctx, similarity);
}

int sqlite3_extension_init(sqlite3 *db, char **pzErrMsg, const sqlite3_api_routines *pApi) {
  SQLITE_EXTENSION_INIT2(pApi);

  return sqlite3_create_function(db, "similarity", 2, SQLITE_ANY, NULL, vector_cosine_similarity, NULL, NULL);
}
