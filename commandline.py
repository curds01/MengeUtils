## November 8, 2006
## Sean Curtis
##
## Class to handle command line arguments.
##
## It assumes command line arguments come in the following forms:
##        -param
##        -param arg
##        -param arg1 arg2 ... argN
##        -param must be a variable which starts with an alpha character        
##
## The input is the list that sys.argv provides (minus the sys.argv[0])
## Provides a common interface for parsing such an argument list and extracting values
##
## Does NOT allow for duplicate params

class ParamManager:
    """Manages command line arguments and parameters"""
    def __init__(self, args = None ):
        self.params = {}
        if ( args != None ):
            self.parseArgs( args )

    def __clear( self ):
        """Clears the set"""
        self.params = {}
        
    def error( self, msg = "Encountered error parsing arguments" ):
        """Clears the set"""
        self.__clear()
        raise IOError, msg

    def parseArgs( self, args ):
        """Parse the argument list and set up accessors"""
        self.__clear()
        currParam = None
        currArg = []
        for i in range( len(args) ):
            token = args[i]
            if ( token.startswith( '-' ) ):
                try:
                    currArg.append( float(token) )  # valid number is NOT a new param
                    if ( not currParam ):
                        self.error("Trying to define a value without having a parameter: %s" % (token))
                except ValueError:                   # if not a valid number, it must be a new param
                    if ( currParam ):
                        if ( not currArg ):             # if no current arguments, simply store a list of True
                            self.params[currParam] = (True, )
                        else:
                            self.params[currParam] = list(currArg)
                        currArg = []
                    currParam = token[1:]
                    if ( self.params.has_key(currParam) ):
                        self.error("Parameter defined twice")
            else:
                if ( not currParam ):
                    self.error("Trying to define a value without having a parameter: %s" % (token))
                currArg.append( token )
        if ( currParam ):
            if ( not currArg ):
                currArg = [True]
            self.params[currParam] = list(currArg)
                        

    def __getitem__( self, key ):
        """Returns a value if the parameter is defined, None otherwise"""
        if self.params.has_key( key ):
            return self.params[key]


## Class to handle SIMPLE command line arguments.
##
## Similar to the ParamManger, except it only allows
## unary and binary arguments such as:
##  -param1 
##  -param1 -arg1 -param2 -arg2       
        
class SimpleParamManager:
    """Manages command line arguments and parameters"""
    def __init__(self, args = None, defaults = None ):
        self.params = {}
        if ( args != None ):
            self.parseArgs( args, defaults )

    def __clear( self ):
        """Clears the set"""
        self.params = {}
        
    def error( self, msg = "Encountered error parsing arguments" ):
        """Clears the set"""
        self.__clear()
        raise IOError, msg

    def parseArgs( self, args, defaults ):
        """Parse the argument list and set up accessors"""
        self.__clear()
        if ( defaults ):
            for key, value in defaults.items():
                self.params[ key ] = value

        i = 0
        while ( i < len( args ) ): 
            token = args[i]
            if ( token.startswith( '-' ) ):
                currParam = token[1:]
                token = args[i + 1]
                try:
                    val = float( token )
                    isNumber = True
                except:
                    isNumber = False
                if ( token.startswith( '-' ) and not isNumber ):
                     # unary argument - it is SUPPOSED to be binary if it is already entered -- do nothing and use default
                     if ( not self.params.has_key( currParam ) ):
                         self.params[ currParam ] = True
                     i += 1
                else:
                    self.params[ currParam ] = token
                    i += 2
            else:
                self.error( 'Expected parameter, found %s' % token )

    def __getitem__( self, key ):
        """Returns one of three things: None (if key isn't present)(unless a default was provided), a string if there was a key and an argument, a boolean if it was a unary parameter"""
        if self.params.has_key( key ):
            return self.params[key]
        else:
            return None


if __name__ == "__main__":
    pMan = ParamManager()

    print "\nValid arguments test"    
    args = ['-in', '-front', '17.3', '-back', '10', '-heights', '3', 'test', 'bob']
    pMan.parseArgs( args )
    testArgs = ['in', 'front', 'junk', 'heights']
    for tArg in testArgs:
        val = pMan[tArg]
        if ( val != None ):
            print "arg %s had value %s" % (tArg, val )
        else:
            print "arg %s was not defined" % (tArg)

    print "\nInvalid: setting value without param"    
    args = [ '-1', '-in', '-front', '17.3', '-back', '10', '-heights', '3', 'test', 'bob']
    try:
        pMan.parseArgs( args )
    except IOError, e:
        print e
    else:  
        print "!!! THIS SHOULDN'T PRINT!!!"

    print "\nInvalid: two duplicate parameters"    
    args = [ '-in', '-front', '17.3', '-back', '10', '-heights', '3', 'test', '-in', 'bob']
    try:
        pMan.parseArgs( args )
    except IOError, e:
        print e
    else:  
        print "!!! THIS SHOULDN'T PRINT!!!"        
    

        