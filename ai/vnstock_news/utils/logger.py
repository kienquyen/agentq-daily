import logging
def setup_logger(name,debug=False):
	'\n    Sets up a logger with the given name and level.\n    \n    Parameters:\n        name (str): The name of the logger.\n        debug (bool): Whether to enable debug logging.\n        \n    Returns:\n        logging.Logger: Configured logger instance.\n    ';A=logging.getLogger(name)
	if A.handlers:return A
	if debug:C=logging.DEBUG;A.setLevel(C);B=logging.StreamHandler();B.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'));A.addHandler(B)
	else:A.addHandler(logging.NullHandler());A.propagate=False
	return A