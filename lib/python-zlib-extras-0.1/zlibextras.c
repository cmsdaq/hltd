/*
 * zlibextras.c - Python extension interfacing to the Linux inotify subsystem
 *
 * Copyright 2006 Bryan O'Sullivan <bos@serpentine.com>
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of version 2.1 of the GNU Lesser General
 * Public License, incorporated herein by reference.
 */

#include <Python.h>
#include <stdint.h>
#include <zlib.h>

static PyObject * zlibextras_crc32_combine(PyObject *self, PyObject *args)
{
  uint32_t crc1, crc2;
  uint64_t len2;
  int32_t crc3_signed;
  //if (!PyArg_ParseTuple(args, "s#|I:crc32_combine", &crc1, &crc2, &len2))
  if (!PyArg_ParseTuple(args, "IIk", &crc1, &crc2, &len2))
    return NULL;
  /* In Python 2.x we return a signed integer regardless of native platform
   * * long size (the 32bit unsigned long is treated as 32-bit signed and sign
   * * extended into a 64-bit long inside the integer object). 3.0 does the
   * * right thing and returns unsigned. http://bugs.python.org/issue1202 */
  crc3_signed = (int32_t)crc32_combine(crc1, crc2, len2);
  return PyLong_FromLong(crc3_signed);
}

static PyObject * zlibextras_adler32_combine(PyObject *self, PyObject *args)
{
  uint32_t adler1, adler2;
  uint64_t len2;
  int32_t adler3_signed;
  //if (!PyArg_ParseTuple(args, "s#|I:crc32_combine", &crc1, &crc2, &len2))
  if (!PyArg_ParseTuple(args, "IIk", &adler1, &adler2, &len2))
    return NULL;
  /* In Python 2.x we return a signed integer regardless of native platform
   * * long size (the 32bit unsigned long is treated as 32-bit signed and sign
   * * extended into a 64-bit long inside the integer object). 3.0 does the
   * * right thing and returns unsigned. http://bugs.python.org/issue1202 */
  adler3_signed = (int32_t)adler32_combine(adler1, adler2, len2);
  return PyLong_FromLong(adler3_signed);
}

static PyMethodDef ZlibExtrasMethods[] = {
    {"crc32_combine",  zlibextras_crc32_combine, METH_VARARGS, "Combine crc32 checksums."},
    {"adler32_combine",  zlibextras_adler32_combine, METH_VARARGS, "Combine adler32 checksums."},
    {NULL, NULL, 0, NULL}
};

#if PY_MAJOR_VERSION == 2
PyMODINIT_FUNC init_zlibextras(void)
{
    (void) Py_InitModule("_zlibextras", ZlibExtrasMethods);
}

PyMODINIT_FUNC initzlibextras(void)
{
    (void) Py_InitModule("zlibextras", ZlibExtrasMethods);
}

#elif PY_MAJOR_VERSION == 3

static char doc[] = "binding for zlib adler32_combine and crc32_combine";

static struct PyModuleDef _zlibdef = {
    PyModuleDef_HEAD_INIT,
    "_zlibextras",
    doc,
    -1,
    ZlibExtrasMethods
};

static struct PyModuleDef zlibdef = {
    PyModuleDef_HEAD_INIT,
    "zlibextras",
    doc,
    -1,
    ZlibExtrasMethods
};


PyObject*  PyInit__zlibdef(void)
{
    return PyModule_Create(&_zlibdef);
}

PyObject*  PyInit_zlibdef(void)
{
    return PyModule_Create(&zlibdef);
}
#endif
