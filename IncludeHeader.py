# This file contains standard including file for the objreader
import os
import sys
TOP_DIR = os.path.dirname( os.path.dirname(__file__) )

sys.path.insert( 0, TOP_DIR + r'\objreader' )
sys.path.insert( 1, TOP_DIR + r'\density' )
