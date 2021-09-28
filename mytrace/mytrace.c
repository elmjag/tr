#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include "frameobject.h"

static void print_what(int what)
{
    switch(what)
    {
       case PyTrace_CALL:
           printf("PyTrace_CALL");
           break;
       case PyTrace_EXCEPTION:
           printf("PyTrace_EXCEPTION");
           break;
       case PyTrace_LINE:
           printf("PyTrace_LINE");
           break;
       case PyTrace_RETURN:
           printf("PyTrace_RETURN");
           break;
       case PyTrace_C_CALL:
           printf("PyTrace_C_CALL");
           break;
       case PyTrace_C_EXCEPTION:
           printf("PyTrace_C_EXCEPTION");
           break;
       case PyTrace_C_RETURN:
           printf("PyTrace_C_RETURN");
           break;
       case PyTrace_OPCODE:
           printf("PyTrace_OPCODE");
           break;
       default:
            printf("unknown what %d", what);
    }
}

static int
_trace_trace(PyObject *obj, PyFrameObject *frame, int what, PyObject *arg)
{
    frame->f_trace_opcodes = 1;

    print_what(what);
    printf(" _trace_trace what %d\n", what);

    if (what == PyTrace_C_RETURN)
    {
        printf("the return of the C stacktop %p\n", frame->f_stacktop);
    }

    return 0;
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

    PyObject **stacktop = frame->f_stacktop;

    if (stacktop == NULL)
    {
        printf("nothig to peek at\n");
        Py_RETURN_NONE;
    }

    PyObject *value = stacktop[-(stack_position)];
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

    PyObject **stacktop = frame->f_stacktop;

    if (stacktop == NULL)
    {
        printf("no stack it seems\n");
    }

    Py_DECREF(stacktop[-(stack_position)]);
    stacktop[-(stack_position)] = value;
    Py_INCREF(value);

    Py_RETURN_NONE;
}


static PyObject *
mytrace_init(PyObject *self, PyObject *args)
{
    if (!PyGILState_Check())
    {
        printf("I don't have the GIL, panic....\n");
        abort();
    }

    PyEval_SetTrace(_trace_trace, NULL);
    PyEval_SetProfile(_trace_trace, NULL);

    Py_RETURN_NONE;
}

static PyMethodDef SpamMethods[] = {
    {"init",  mytrace_init, METH_VARARGS, "TBD"},
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