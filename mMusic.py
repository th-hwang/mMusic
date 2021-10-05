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
        logger.debug("Initializing HandleDB Class")
        logger.debug("Connecting to the database sever")
        try:
            self.dbCon = MySQLdb.connect(
                host=dbHost, user=dbUser, passwd=dbPasswd, charset='utf8')
            logger.debug("Success to connect to the database sever")
        except:
            logger.error("Fail to connect to the database sever")
            raise

    def __del__(self):
        logger.debug("Deleting HandleDB Class")
        self.dbCon.close()

    def sendQuery(self, SQL, data=(), mode=""):
        logger.debug(
            "sendQuery with SQL = [%s] and data = [%s]", SQL, data)

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
                "Error in sendQuery() with SQL = [%s] and data = [%s]", SQL, data)
            logger.error("Error in sendQuery() with error messsage %s", e)

            if (mode == "DML"):
                self.dbCon.rollback()
                return False
        finally:
            cursor.close()

    def isExistDB(self, dbName):
        logger.debug(
            "Checking the existence of the database [%s]", dbName)

        sql = """Show databases like '{db}';""".format(db=dbName)
        return len(self.sendQuery(sql)) > 0

    def makeDB(self, dbName):
        if(not self.isExistDB(dbName)):
            logger.debug("Cannot find the database [%s]", dbName)
            logger.debug("Creating the database [%s]", dbName)

            sql = """CREATE DATABASE IF NOT EXISTS {db};""".format(
                db=dbName)
            return self.sendQuery(sql) != None
        else:
            logger.debug("The database [%s] exists", dbName)
            return False

    def deleteDB(self, dbName):
        if(self.isExistDB(dbName)):
            logger.debug("Deleting the database [%s]", dbName)

            sql = """DROP DATABASE IF EXISTS {db};""".format(
                db=dbName)
            return self.sendQuery(sql) != None
        else:
            logger.debug(
                "Cannot find the database [%s] and thus cannot delete it", dbName)
            return False

    def isExistTB(self, dbName, tbName):

        if (self.isExistDB(dbName)):
            logger.debug(
                "Checking the existence of the user table [%s] in the database [%s]", tbName, dbName)

            sql = """Show tables in {db} like '{tb}';""".format(
                db=dbName, tb=tbName)

            return len(self.sendQuery(sql)) > 0
        else:
            logger.debug("There is no database [%s]", dbName)
            return False

    def makeTB(self):
        # design eto rewrite the methon in the child class
        pass

    def deleteTB(self, dbName, tbName):
        if(self.isExistTB(dbName, tbName)):
            logger.debug(
                "Deleting the user table [%s] in the database [%s]", tbName, dbName)

            sql = """DROP TABLE IF EXISTS {db}.{tb};""".format(
                db=dbName, tb=tbName)
            return self.sendQuery(sql) != None
        else:
            logger.debug(
                "Cannot find the table [%s] in the database [%s] and thus cannot delete it", tbName, dbName)
            return False


class HandleUserDB(HandleDB):

    def __init__(self, dbHost, dbUser, dbPasswd, dbName, tbName):
        logger.debug("Initializing HandleUserDB Class")
        super().__init__(dbHost, dbUser, dbPasswd)

        self.dbName = dbName
        self.tbName = tbName

        if(not self.isExistDB(self.dbName)):
            self.makeDB(self.dbName)

        if(not self.isExistTB(self.dbName, self.tbName)):
            self.makeTB(self.dbName, self.tbName)

    def __del__(self):
        logger.debug("Deleting HandleUserDB Class")
        super().__del__()

    def makeTB(self, dbName, tbName):
        if (self.isExistDB(dbName)):
            if(not self.isExistTB(dbName, tbName)):
                logger.debug(
                    "Cannot find the user table [%s] in the database [%s]", tbName, self.dbName)
                logger.debug(
                    "Creating the user table [%s] in the database [%s]", tbName, self.dbName)

                sql = """CREATE TABLE IF NOT EXISTS {db}.{tb} (
                        idUser 		int 		unsigned NOT NULL AUTO_INCREMENT,
                        loginID  	varchar(32) NOT NULL,
                        passwd 	    varchar(32) NOT NULL,
                        privilege	boolean     DEFAULT false,
                        deleteflag	boolean     DEFAULT false,
                        PRIMARY KEY (idUser)
                        ) DEFAULT CHARSET=utf8;""".format(db=dbName, tb=tbName)

                return self.sendQuery(sql) != None
            else:
                logger.debug(
                    "The user table [%s] in database [%s] exists", tbName, dbName)
                return False
        else:
            logger.debug(
                "There is no database [%s]", dbName)
            return False

    def isExistUser(self, userInfo):
        logger.debug("Checking the existence of the user [%s] with previlege [%s] in the user table [%s] of the database [%s]",
                     userInfo['uid'], userInfo['privilege'], self.tbName, self.dbName)

        wh = """where """

        if (userInfo['uid'] != ""):
            wh = wh + " and " if len(wh) > 6 else wh
            wh = wh + """loginID='{uid}'""".format(uid=userInfo['uid'])

        if (userInfo['passwd'] != ""):
            wh = wh + " and " if len(wh) > 6 else wh
            wh = wh+"""passwd='{pwd}'""".format(pwd=userInfo['passwd'])

        if (userInfo['privilege'] != ""):
            wh = wh + " and " if len(wh) > 6 else wh
            wh = wh + """privilege={pr}""".format(pr=userInfo['privilege'])

        wh = "" if len(wh) <= 6 else wh

        # need space between table name and where
        sql = """select * from {db}.{tb}""".format(
            db=self.dbName, tb=self.tbName) + " " + wh + ";"

        return len(self.sendQuery(sql)) > 0

    def isExistUID(self, uID):
        logger.debug(
            "Checking if the user ID [%s] exists in User_Table.", userInfo['uid'])
        dummyUser = {'uid': uID, 'passwd': "", 'privilege': ""}

        return self.isExistUser(dummyUser)

    def isFirstUser(self):
        logger.debug(
            "Checking if you are the first user. The first user can have all privilege")
        dummyUser = {'uid': "", 'passwd': "", 'privilege': ""}

        return not self.isExistUser(dummyUser)

    def addUserAccount(self, userInfo):
        userInfo['privilege'] = True if self.isFirstUser() else False

        if (self.isExistUID(userInfo['uid'])):
            logger.error("Your user ID [%s] exists in the user table [%s] of the database [%s]",
                         userInfo['uid'], self.tbName, self.dbName)
            return False

        else:
            logger.debug(
                "Adding userInfo [%s] to the user table [%s] in the database [%s]", userInfo, self.tbName, self.dbName)

            sql = """insert into {db}.{tb} (loginID, passwd, privilege) values ('{uid}','{pwd}',{pr});"""
            sql = sql.format(db=self.dbName, tb=self.tbName,
                             uid=userInfo['uid'], pwd=userInfo['passwd'], pr=userInfo['privilege'])

            return True if self.sendQuery(sql, mode="DML") == None else False

    def rmUserAccount(self, userInfo):
        if (self.isExistUID(userInfo['uid'])):
            logger.debug(
                "Removing the userInfo [%s] from the user table [%s] in the database [%s]", userInfo, self.tbName, self.dbName)

            sql = """delete from {db}.{tb} where loginID= '{uid}'; """
            sql = sql.format(db=self.dbName, tb=self.tbName,
                             uid=userInfo['uid'])

            return True if self.sendQuery(sql, mode="DML") == None else False
        else:
            logger.error("Your user ID [%s] doesnot exist in the user table [%s] of the database [%s] and thus cannot be deleted",
                         userInfo['uid'], self.tbName, self.dbName)
            return False

    def updateUserAccount(self, userInfo):
        if (self.isExistUID(userInfo['uid'])):
            logger.debug(
                "Updating the userInfo [%s] from the user table [%s] in the database [%s]", userInfo, self.tbName, self.dbName)

            sql = """update {db}.{tb} set passwd='{pwd}', privilege={pr} where loginID='{uid}'; """
            sql = sql.format(db=self.dbName, tb=self.tbName,
                             uid=userInfo['uid'], pwd=userInfo['passwd'], pr=userInfo['privilege'])

            return True if self.sendQuery(sql, mode="DML") == None else False
        else:
            logger.error("Your user ID [%s] doesnot exist in the user table [%s] of the database [%s] and thus cannot be updated",
                         userInfo['uid'], self.tbName, self.dbName)
            return False


if __name__ == "__main__":

    # setting define directory
    DB_HOST = "192.168.35.215"
    DB_USER = "kodi"
    DB_PASSWD = "kodi"
    DB_NAME = "Home_Music"
    USER_TB_NAME = "User_Table"
    HOME_DIR = "/common/Musics/"

    logger = logging.getLogger(DB_USER)
    fomatter = logging.Formatter(
        '[%(levelname)s|%(filename)s:%(lineno)s] %(asctime)s > %(message)s')

    streamHandler = logging.StreamHandler()
    streamHandler.setFormatter(fomatter)
    logger.addHandler(streamHandler)
    logger.setLevel(logging.DEBUG)

    hUserDB = HandleUserDB(DB_HOST, DB_USER, DB_PASSWD, DB_NAME, USER_TB_NAME)

# hUserTB.isExistUser(USER_TB_NAME, userInfo)
    # userInfo = {'uid': "", 'passwd': DB_PASSWD, 'privilege': False}
    # userInfo = {'uid': "", 'passwd': "", 'privilege': False}
    userInfo = {'uid': DB_USER, 'passwd': "ll", 'privilege': True}
    # userInfo = {'uid': "kk", 'passwd': "kk", 'privilege': False}

    # print(hUserDB.isExistUser(userInfo))
    print(hUserDB.isExistUID(userInfo['uid']))
    print(hUserDB.isFirstUser())
    # print(hUserDB.addUserAccount(userInfo))
    print(hUserDB.updateUserAccount(userInfo))
    print(hUserDB.rmUserAccount(userInfo))
