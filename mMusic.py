#!/Users/taehyunghwang/pyWorks/mMusic/.venv/bin/python
# -*- coding: utf-8 -*-
# ver 0.1 : release 19.08.07
# ver 0.2 : support ranking  based on melon top 100 chart
# ver 0.3 : support updating database based on music in the directory
# ver 0.4 : [bug fix] change handling escape characters
# ver 0.5 : change to python3 and make class

import os
import shutil

import logging
import logging.handlers
import MySQLdb
from mutagen.id3 import ID3


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

    def _sendQuery(self, SQL, data=(), mode=""):
        logger.debug(
            "_sendQuery with SQL = [%s] and data = [%s]", SQL, data)

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
                "Error in _sendQuery() with SQL = [%s] and data = [%s]", SQL, data)
            logger.error("Error in _sendQuery() with error messsage %s", e)

            if (mode == "DML"):
                self.dbCon.rollback()
                return False
        finally:
            cursor.close()

    def isExistDB(self, dbName):
        logger.debug(
            "Checking the existence of the database [%s]", dbName)

        sql = """Show databases like '{db}';""".format(db=dbName)
        return len(self._sendQuery(sql)) > 0

    def makeDB(self, dbName):
        if(not self.isExistDB(dbName)):
            logger.debug("Cannot find the database [%s]", dbName)
            logger.debug("Creating the database [%s]", dbName)

            sql = """CREATE DATABASE IF NOT EXISTS {db};""".format(
                db=dbName)
            return self._sendQuery(sql) != None
        else:
            logger.debug("The database [%s] exists", dbName)
            return False

    def deleteDB(self, dbName):
        if(self.isExistDB(dbName)):
            logger.debug("Deleting the database [%s]", dbName)

            sql = """DROP DATABASE IF EXISTS {db};""".format(
                db=dbName)
            return self._sendQuery(sql) != None
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

            return len(self._sendQuery(sql)) > 0
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
            return self._sendQuery(sql) != None
        else:
            logger.debug(
                "Cannot find the table [%s] in the database [%s] and thus cannot delete it", tbName, dbName)
            return False

    def _where(self, dic):
        # make [ where key1='value1' and key2 = 'value2'; ]
        # sql = """select * from {db}.{tb} where loginID = '{loginID}' and passwd= '{passwd}' and privilege={privilige}"""
        wh_Org = """ where """
        wh = wh_Org
        for key, value in dic.items():
            if not value == "":
                if len(wh) > len(wh_Org):
                    wh = wh + " and "
                if type(value) == str:
                    wh = wh + \
                        """{key}='{value}'""".format(key=key, value=value)
                else:
                    wh = wh + """{key}={value}""".format(key=key, value=value)

        return wh + ";" if len(wh) > len(wh_Org) else ";"

    def _values(self, dic):
        # make [ (key1, key2, key3) values ('value1','value2', 'value3'); ]
        # sql = """insert {db}.{tb} (loginID, passwd, privilege) values ('{loginID}', '{passwd}', {privilige})"""
        val_Org = " ( "
        keys = val_Org
        vals = val_Org
        for key, value in dic.items():
            if not value == "":
                if len(keys) > len(val_Org):
                    keys = keys + ", "
                    vals = vals + ", "
                if type(value) == str:
                    keys = keys + """{key}""".format(key=key)
                    vals = vals + """'{val}'""".format(val=value)
                else:
                    keys = keys + """{key}""".format(key=key)
                    vals = vals + """{val}""".format(val=value)

        if len(keys) > len(val_Org):
            return keys + " ) values " + vals + " );"

        else:
            logger.error("no data to be updated")
            return

    def _set(self, dic):
        # make [ set key1 = 'value1', key2 = 'value1]
        # sql = """update {db}.{tb} set passwd='{pwd}', privilege={pr} where loginID='{loginID}'; """
        se_Org = " set "
        se = se_Org

        for key, value in dic.items():
            if not value == "":
                if len(se) > len(se_Org):
                    se = se + " , "
                if type(value) == str:
                    se = se + \
                        """{key}='{value}'""".format(key=key, value=value)
                else:
                    se = se + """{key}={value}""".format(key=key, value=value)

        return se if len(se) > len(se_Org) else ""


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
                    "Cannot find the user table [%s] in the database [%s]", tbName, dbName)
                logger.debug(
                    "Creating the user table [%s] in the database [%s]", tbName, dbName)

                sql = """CREATE TABLE IF NOT EXISTS {db}.{tb} (
                        idUser 		int 		unsigned NOT NULL AUTO_INCREMENT,
                        loginID  	varchar(32) NOT NULL,
                        passwd 	    varchar(64) NOT NULL,
                        privilege	boolean     DEFAULT false,
                        deleteflag	boolean     DEFAULT false,
                        PRIMARY KEY (idUser)
                        ) DEFAULT CHARSET=utf8;""".format(db=dbName, tb=tbName)

                return self._sendQuery(sql) != None
            else:
                logger.debug(
                    "The user table [%s] in database [%s] exists", tbName, dbName)
                return False
        else:
            logger.debug(
                "There is no database [%s]", dbName)
            return False

    def isExistUser(self, userInfo):
        logger.debug(
            "Checking the existence of the user in the user table [%s] of the database [%s]", self.tbName, self.dbName)

        # need space between table name and where
        sql = """select * from {db}.{tb}""".format(
            db=self.dbName, tb=self.tbName) + " " + self._where(userInfo)

        return len(self._sendQuery(sql)) > 0

    def isExistLoginID(self, loginID):
        logger.debug(
            "Checking if the user ID [%s] exists in User_Table [%s] of the database [%s].", loginID, self.tbName, self.dbName)

        return self.isExistUser({'loginID': loginID})

    def isFirstUser(self):
        logger.debug(
            "Checking if you are the first user. The first user can have all privilege")

        return not self.isExistUser({})

    def isAdminLogindID(self, loginID):
        return self.getUserAccount(loginID)[0]['privilege']

    def addUserAccount(self, userInfo):

        if (self.isExistLoginID(userInfo['loginID'])):
            logger.error("Your user ID [%s] exists in the user table [%s] of the database [%s]",
                         userInfo['loginID'], self.tbName, self.dbName)
            return False

        else:
            logger.debug(
                "Adding userInfo [%s] to the user table [%s] in the database [%s]", userInfo, self.tbName, self.dbName)

            if self.isFirstUser():
                userInfo['privilege'] = True

            sql = """insert into {db}.{tb} """.format(
                db=self.dbName, tb=self.tbName) + self._values(userInfo)

            return True if self._sendQuery(sql, mode="DML") == None else False

    def rmUserAccount(self, loginID):
        if (self.isExistLoginID(loginID)):
            logger.debug(
                "Removing the user ID [%s] from the user table [%s] in the database [%s]", loginID, self.tbName, self.dbName)

            sql = """delete from {db}.{tb}""".format(
                db=self.dbName, tb=self.tbName) + self._where({'loginID': loginID})

            return True if self._sendQuery(sql, mode="DML") == None else False
        else:
            logger.error("Your user ID [%s] doesnot exist in the user table [%s] of the database [%s] and thus cannot be deleted",
                         loginID, self.tbName, self.dbName)
            return False

    def getUserAccount(self, loginID):
        if (self.isExistLoginID(loginID)):
            logger.debug(
                "Getting the userInfo of user ID [%s] from the user table [%s] in the database [%s]", loginID, self.tbName, self.dbName)
            sql = """select * from {db}.{tb}""".format(
                db=self.dbName, tb=self.tbName) + self._where({'loginID': loginID})

            rlt = self._sendQuery(sql)
            if not rlt == None:
                result = []
                for v in rlt:
                    result.append(
                        {'loginID': v[1], 'passwd': v[2], 'privilege': v[3]})
                return result
            else:
                logger.debug("Cannot find the user account [%s]", loginID)
                return None
        else:
            logger.error("Your user ID [%s] doesnot exist in the user table [%s] of the database [%s] and thus cannot get account info",
                         loginID, self.tbName, self.dbName)
        return None

    def updateUserAccount(self, userInfo):

        if (self.isExistLoginID(userInfo['loginID'])):
            logger.debug(
                "Updating the userInfo [%s] from the user table [%s] in the database [%s]", userInfo, self.tbName, self.dbName)

            sql = """update {db}.{tb}""".format(db=self.dbName, tb=self.tbName) + self._set(
                userInfo) + self._where({'loginID': userInfo['loginID']})

            return True if self._sendQuery(sql, mode="DML") == None else False
        else:
            logger.error("Your user ID [%s] doesnot exist in the user table [%s] of the database [%s] and thus cannot be updated",
                         userInfo['loginID'], self.tbName, self.dbName)
            return False


class HandleMusicDB(HandleDB):

    def __init__(self, dbHost, dbUser, dbPasswd, dbName, tbName):
        logger.debug("Initializing HandleMusicDB Class")
        super().__init__(dbHost, dbUser, dbPasswd)

        self.dbName = dbName
        self.tbName = tbName

        if(not self.isExistDB(self.dbName)):
            self.makeDB(self.dbName)

        if(not self.isExistTB(self.dbName, self.tbName)):
            self.makeTB(self.dbName, self.tbName)

    def __del__(self):
        logger.debug("Deleting HandleMusicDB Class")
        super().__del__()

    def makeTB(self, dbName, tbName):
        if (self.isExistDB(dbName)):
            if(not self.isExistTB(dbName, tbName)):
                logger.debug(
                    "Cannot find the music table [%s] in the database [%s]", tbName, dbName)
                logger.debug(
                    "Creating the music table [%s] in the database [%s]", tbName, dbName)

                sql = """CREATE TABLE IF NOT EXISTS {db}.{tb} (
                        idmusic 		int 		unsigned NOT NULL AUTO_INCREMENT,
                        title		varchar(256),
                        artist 		varchar(256),
                        album 		varchar(256),
                        sdate 		date,
                        genre 		varchar(32),
                        filename 	varchar(256),
                        imgname 	varchar(256),
                        lyricname 	varchar(256),
                        currentrank	int		unsigned,
                        favor		int		unsigned,
                        deleteflag	int		unsigned,
                        PRIMARY KEY (idmusic)
                        ) DEFAULT CHARSET=utf8;""".format(db=dbName, tb=tbName)

                return self._sendQuery(sql) != None
            else:
                logger.debug(
                    "The user table [%s] in database [%s] exists", tbName, dbName)
                return False
        else:
            logger.debug(
                "There is no database [%s]", dbName)
            return False

    def isExistMusic(self, musicInfo):
        logger.debug(
            "Checking the existence of the music [%s] in the music table [%s] of the database [%s]", musicInfo, self.tbName, self.dbName)

        # need space between table name and where
        sql = """select * from {db}.{tb}""".format(
            db=self.dbName, tb=self.tbName) + " " + self._where(musicInfo)

        return len(self._sendQuery(sql)) > 0

    def isExistMusicArtistTitle(self, artist, title):
        logger.debug(
            "Checking if the music info record having title [%s] and artist [%s] exists in music table [%s] of database [%s].", title, artist, self.tbName, self.dbName)

        return self.isExistMusic({'title': title, 'artist': artist})

    def addMusicRecord(self, musicInfo):

        if (self.isExistMusicArtistTitle(musicInfo['artist'], musicInfo['title'])):
            logger.error("The music info record having title [%s] and artist [%s] exists in the music table [%s] of the database [%s] and thus cannot be added",
                         musicInfo['title'], musicInfo['artist'], self.tbName, self.dbName)
            return False

        else:
            logger.debug(
                "Adding the music info record [%s] to the music table [%s] in the database [%s]", musicInfo, self.tbName, self.dbName)

            sql = """insert into {db}.{tb} """.format(
                db=self.dbName, tb=self.tbName) + self._values(musicInfo)

            return True if self._sendQuery(sql, mode="DML") == None else False

    def rmMusicRecordArtistTitle(self, artist, title):

        if (self.isExistMusicArtistTitle(artist, title)):
            logger.debug(
                "Removing the muisc info record having title [%s] and artist [%s] from the music table [%s] in the database [%s]", title, artist, self.tbName, self.dbName)

            sql = """delete from {db}.{tb}""".format(
                db=self.dbName, tb=self.tbName) + self._where({'title': title, 'artist': artist})

            return True if self._sendQuery(sql, mode="DML") == None else False
        else:
            logger.error(
                "The music info record having title [%s] and artist [%s] doesnot exist in the music table [%s] of the database [%s] and thus cannot be deleted", title, artist, self.tbName, self.dbName)
            return False

    def getMusicRecordArtistTitle(self, artist, title):
        if (self.isExistMusicArtistTitle(artist, title)):
            logger.debug(
                "Getting the music info record having title [%s] and artist [%s] from the music table [%s] in the database [%s]", title, artist, self.tbName, self.dbName)
            sql = """select * from {db}.{tb}""".format(
                db=self.dbName, tb=self.tbName) + self._where({'title': title, 'artist': artist})

            rlt = self._sendQuery(sql)
            if not rlt == None:
                result = []
                for v in rlt:
                    result.append(
                        {'title': v[1], 'artist': v[2], 'album': v[3], 'sdate': v[4], 'genre': v[5], 'filename': v[6], 'imgname': v[7], 'lyricname': v[8], 'currentrank': v[9], 'favor': v[10], 'deleteflag': v[11]})
                return result
            else:
                logger.debug(
                    "Cannot find the music info record having title [%s] and artist [%s]", title, artist)
                return None
        else:
            logger.error("The music info record having title [%s] and artist [%s] doesnot exist in the music table [%s] of the database [%s] and thus cannot get account info",
                         title, artist, self.tbName, self.dbName)
        return None

    def updateMusicRecord(self, musicInfo):

        if (self.isExistMusicArtistTitle(musicInfo['artist'], musicInfo['title'])):
            logger.debug(
                "Updating the music info record [%s] from the user table [%s] in the database [%s]", musicInfo, self.tbName, self.dbName)

            sql = """update {db}.{tb}""".format(db=self.dbName, tb=self.tbName) + self._set(
                musicInfo) + self._where({'title': musicInfo['title'], 'artist': musicInfo['artist']})

            return True if self._sendQuery(sql, mode="DML") == None else False
        else:
            logger.error("The music info record having title [%s] and artist [%s] doesnot exist in the music table [%s] of the database [%s] and thus cannot be updated",
                         musicInfo['artist'], musicInfo['title'], self.tbName, self.dbName)
            return False


class HandleFile():
    def mkDir(self, strDir):
        if not os.access(strDir, os.F_OK):
            try:
                return os.makedirs(strDir, mode=0o775)
            except:
                logger.error("Error in mkDir() [%s]", strDir)
                raise
        else:
            logger.error("Error in rmDir(). [%s] is not accessible", strDir)
            raise

    def rmDir(self, strDir):
        if os.access(strDir, os.F_OK):
            try:
                return shutil.rmtree(strDir)
            except:
                logger.error("Error in rmDir() [%s]", strDir)
                raise
        else:
            logger.error("Error in rmDir(). [%s] is not accessible", strDir)
            raise

    def mkFileList(self, fileList):
        try:
            result = []
            for ff in fileList if type(fileList) is list else [fileList]:
                if(os.path.isdir(ff)):
                    logger.info(
                        "%s is directory. Walk into the directory " % ff)
                    if os.listdir(ff):
                        for (path, dirs, files) in os.walk(ff):
                            for ff2 in files:
                                fName = os.path.abspath(
                                    os.path.join(path, ff2))
                                result.append(fName)
                    else:
                        logger.info("[Skip] " + ff +
                                    " is empty .......... [Skip]")
                else:
                    result.append(os.path.abspath(ff))
            return result
        except:
            logger.error("Error in mkFileList() input = %s", fileList)
            raise


def showall(hDB):
    print(hDB._sendQuery(
        "select * from {db}.{tb}".format(db=hDB.dbName, tb=hDB.tbName)))


def showall_test(hDB, wh):
    print(hDB._sendQuery(
        "select * from {db}.{tb} where loginID = '{wh}';".format(db=hDB.dbName, tb=hDB.tbName, wh=wh)))


def showall_test1(hDB, wh):
    print(hDB._sendQuery("select * from %(db)s.%(tb)s where loginID = %(id)s",
          data={'db': hDB.dbName, 'tb': hDB.tbName, 'id': wh}))


def test_hUserDB(hUserDB, userInfo):
    print("Check Database : " +
          "[OK]" if hUserDB.isExistDB(hUserDB.dbName) else "[ERROR]")

    print("Check Table : " +
          "[OK]" if hUserDB.isExistTB(hUserDB.dbName, hUserDB.tbName) else "[ERROR]")

    print("Add UserAccount : ", end="")
    print(userInfo)
    hUserDB.addUserAccount(userInfo)
    print("Get UserAccount : ", end="")
    print(hUserDB.getUserAccount(userInfo['loginID']))

    print("Add UserAccount when account exists: ", end="")
    print(userInfo)
    hUserDB.addUserAccount(userInfo)

    print("Update UserAccount : ", end="")
    userInfo['passwd'] = "change"
    print(userInfo)
    hUserDB.updateUserAccount(userInfo)
    print("Get UserAccount : ", end="")
    print(hUserDB.getUserAccount(userInfo['loginID']))

    print("Remove UserAccount :", end="")
    print(userInfo)
    hUserDB.rmUserAccount(userInfo['loginID'])
    print("Get UserAccount : ", end="")
    print(hUserDB.getUserAccount(userInfo['loginID']))

    print("Remove UserAccount when account doesn't exist :", end="")
    print(userInfo)
    hUserDB.rmUserAccount(userInfo['loginID'])
    print("Get UserAccount : ", end="")
    print(hUserDB.getUserAccount(userInfo['loginID']))


def test_hMusicDB(hMusicDB, musicInfo):
    print("Check Database : " +
          "[OK]" if hMusicDB.isExistDB(hMusicDB.dbName) else "[ERROR]")

    print("Check Table : " +
          "[OK]" if hMusicDB.isExistTB(hMusicDB.dbName, hMusicDB.tbName) else "[ERROR]")

    print("Add music info record :", end="")
    print(musicInfo)
    hMusicDB.addMusicRecord(musicInfo)
    print("Get music info record :", end="")
    print(hMusicDB.getMusicRecordArtistTitle(
        musicInfo['artist'], musicInfo['title']))

    print("Add music info record when the music record exists:", end="")
    print(musicInfo)
    hMusicDB.addMusicRecord(musicInfo)

    print("Update music info record : ", end="")
    musicInfo['genre'] = "change"
    print(musicInfo)
    hMusicDB.updateMusicRecord(musicInfo)
    print("Get music Info record :", end="")
    print(hMusicDB.getMusicRecordArtistTitle(
        musicInfo['artist'], musicInfo['title']))

    print("Remove music info record :", end="")
    print(musicInfo)
    hMusicDB.rmMusicRecordArtistTitle(musicInfo['artist'], musicInfo['title'])
    print("Get music Info record :", end="")
    print(hMusicDB.getMusicRecordArtistTitle(
        musicInfo['artist'], musicInfo['title']))

    print("Remove music info record when the music record doesn't exist :", end="")
    print(musicInfo)
    hMusicDB.rmMusicRecordArtistTitle(musicInfo['artist'], musicInfo['title'])
    print("Get music Info record :", end="")
    print(hMusicDB.getMusicRecordArtistTitle(
        musicInfo['artist'], musicInfo['title']))


if __name__ == "__main__":

    # setting define directory
    DB_HOST = "192.168.35.215"
    DB_USER = "kodi"
    DB_PASSWD = "kodi"
    DB_NAME = "Home_Music"
    USER_TB_NAME = "User_Table"
    HOME_DIR = "/common/Musics/"
    TEMP_UID = "karlken"

    logger = logging.getLogger(DB_USER)
    fomatter = logging.Formatter(
        '[%(levelname)s|%(filename)s:%(lineno)s] %(asctime)s > %(message)s')

    streamHandler = logging.StreamHandler()
    streamHandler.setFormatter(fomatter)
    logger.addHandler(streamHandler)
    logger.setLevel(logging.INFO)
    # logger.setLevel(logging.DEBUG)

    # hUserDB = HandleUserDB(DB_HOST, DB_USER, DB_PASSWD, DB_NAME, USER_TB_NAME)
    # TEST: hUserDB
    # logger.setLevel(logging.INFO)
    # userInfo = {'loginID': DB_USER, 'passwd': DB_PASSWD, 'privilege': True}
    # test_hUserDB(hUserDB, userInfo)
    # showall_test(hUserDB, """' or 1=1 --'""")
    # showall_test1(hUserDB, """' or 1=1--'""")

    # hMusicDB = HandleMusicDB(DB_HOST, DB_USER, DB_PASSWD, DB_NAME, TEMP_UID)
    # TEST : hMusicDB
    # logger.setLevel(logging.INFO)
    # musicInfo = {'title': '노래', 'artist': '아이유', 'album': '발라드', 'sdate': 20211011, 'genre': '발라드', 'filename': 'file_here',
    #              'imgname': 'img_here', 'lyricname': 'lyric_here', 'currentrank': 999, 'favor': 1, 'deleteflag': 0}
    # test_hMusicDB(hMusicDB, musicInfo)

    hFile = HandleFile()
    print(hFile.mkFileList(["imsi"]))

    # tag = ID3("002.mp3")
    # print(tag['TIT2'].text[0])
    # hMusicDB.addMusicRecord(
    #     {'title': tag['TIT2'].text[0], 'artist': tag['TPE1'].text[0]})
