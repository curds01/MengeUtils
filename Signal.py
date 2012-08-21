# Signal class -- used in conjunciton with kernel.  This is convolved with the kernel

class Signal:
    '''The basic signal class - it represents a mathematical function to be conolved with a kernel'''
    pass

class DiracSignal( Signal ):
    '''A signal based on the summation of many translated dirac functions'''
    pass

class FieldSignal( Signal ):
    '''The discrete representation of a continuous signal defined over a region.'''
    pass
