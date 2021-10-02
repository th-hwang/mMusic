#!/Users/taehyunghwang/pyWorks/mMusic/.venv/bin/python
# -*- coding: utf-8 -*-
# ver 0.1 : release 19.08.07
# ver 0.2 : support ranking  based on melon top 100 chart
# ver 0.3 : support updating database based on music in the directory
# ver 0.4 : [bug fix] change handling escape characters
# ver 0.5 : change to python3 and make class

import MySQLdb
import logging
import logging.handlers


class HandleDB:

    def __init__(self, dbHost, dbUser, dbPasswd):
        logger.debug("Initialize handleDB Class")

        logger.debug("Connecting to the database sever")
        try:
            self.dbCon = MySQLdb.connect(
                host=dbHost, user=dbUser, passwd=dbPasswd, charset='utf8')
            logger.debug("Success to connect to the database sever")
        except:
            logger.error("Fail to connect to the database sever")
            raise

    def sendQuery(self, SQL, data=(), mode=""):
        try:
            cursor = self.dbCon.cursor()
            cursor.execute(SQL, data)
            if (mode == "DML"):
                # dml = data manupulation language, should be commited to change data
                return self.dbCon.commit()
            else:
                return cursor.fetchall()

        except MySQLdb.Error as e:
            logger.error(
                "Error in SendQuery() with SQL = [%s] and data = [%s]", SQL, data)
            logger.error("Error in SendQuery() with error messsage %s", e)

            if (mode == "DML"):
                self.dbCon.rollback()
                return False

        finally:
            cursor.close()

    def isExistDB(self, dbName):

        logger.debug("Checking the existence of the database [%s]", dbName)

        sql = """Show databases like '{db}';""".format(db=dbName)

        return len(self.sendQuery(sql)) > 0

    def isExistTB(self, dbName, tbName):

        if (self.isExistDB(dbName)):

            logger.debug(
                "Checking the existence of the user table [%s] in the database [%s]", tbName, dbName)

            sql = """Show tables in {db} like '{tb}';""".format(
                db=dbName, tb=tbName)
            return len(self.sendQuery(sql)) > 0
        else:
            logger.debug(" There is no database [%s]", dbName)
            return False


if __name__ == "__main__":

    logger = logging.getLogger("kodi")
    fomatter = logging.Formatter(
        '[%(levelname)s|%(filename)s:%(lineno)s] %(asctime)s > %(message)s')

    streamHandler = logging.StreamHandler()
    streamHandler.setFormatter(fomatter)
    logger.addHandler(streamHandler)

    logger.setLevel(logging.DEBUG)
    hDB = HandleDB("192.168.35.215", "kodi", "kodi")
    # print(hDB.isExistDB("Home_Music"))
    print(hDB.isExistTB("Home_Music", "User_Table"))
