import logging;

def loggerInit(logname:str,loglevel:logging._Level)->logging.Logger:
    logging.basicConfig(filename=logname,
                    filemode='a',
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=loglevel)

    logging.info("Running Urban Planning")
    logger = logging.getLogger()
    return logger
    