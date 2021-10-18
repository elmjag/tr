#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include "frameobject.h"

#define TOP()             (stack_pointer[-1])
#define PEEK(n)           (stack_pointer[-(n)])
#define SET(n, v)        (stack_pointer[-(n)] = (v))

static PyObject **
_get_stack_pointer(PyFrameObject *frame)
{
    return frame->f_valuestack + frame->f_stackdepth;
}

static PyObject *
mytrace_peek_stack(PyObject *self, PyObject *args)
{
    PyFrameObject *frame;

    const int stack_position;
    if (!PyArg_ParseTuple(args, "Oi", &frame, &stack_position))
    {
        return NULL;
    }

    PyObject **stack_pointer = _get_stack_pointer(frame);

    if (stack_position > frame->f_stackdepth)
    {
        fprintf(stderr, "peek_stack: stack_position %d > stackdepth %d\n",
                stack_position, frame->f_stackdepth);
        Py_RETURN_NONE;
    }

    PyObject *value = PEEK(stack_position);
    if (value == NULL)
    {
         fprintf(stderr, "peek_stack: value is NULL!\n");
         Py_RETURN_NONE;
    }

    Py_INCREF(value);

    return value;
}

static PyObject *
mytrace_overwrite_stack_value(PyObject *self, PyObject *args)
{
    PyFrameObject *frame;
    PyObject *value;

    const int stack_position;
    if (!PyArg_ParseTuple(args, "OiO", &frame, &stack_position, &value))
    {
        return NULL;
    }

    PyObject **stack_pointer = _get_stack_pointer(frame);

    if (stack_position > frame->f_stackdepth)
    {
        fprintf(stderr, "overwrite_stack_value: stack_position %d > stackdepth %d\n",
                stack_position, frame->f_stackdepth);
        Py_RETURN_NONE;
    }

    Py_DECREF(PEEK(stack_position));
    SET(stack_position, value);
    Py_INCREF(value);

    Py_RETURN_NONE;
}

static PyMethodDef SpamMethods[] = {
    {"peek_stack",  mytrace_peek_stack, METH_VARARGS, "TBD"},
    {"overwrite_stack_value",  mytrace_overwrite_stack_value, METH_VARARGS, "TBD"},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

static struct PyModuleDef spammodule = {
    PyModuleDef_HEAD_INIT,
    "mytrace",   /* name of module */
    NULL, /* module documentation, may be NULL */
    -1,       /* size of per-interpreter state of the module,
                 or -1 if the module keeps state in global variables. */
    SpamMethods
};

PyMODINIT_FUNC
PyInit_mytrace(void)
{
    return PyModule_Create(&spammodule);
}