#!/Users/taehyunghwang/pyWorks/mMusic/.venv/bin/python
# -*- coding: utf-8 -*-
# ver 0.1 : release 19.08.07
# ver 0.2 : support ranking  based on melon top 100 chart
# ver 0.3 : support updating database based on music in the directory
# ver 0.4 : [bug fix] change handling escape characters
# ver 0.5 : change to python3 and make class

import os
import shutil
import pathlib

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

    def _sendQuery(self, SQL, data={}, mode=""):
        logger.debug(
            "_sendQuery with SQL = [%s] and data = [%s]", SQL, data)

        try:
            cursor = self.dbCon.cursor()

            # Database name, table name 은 일반적으로 사용자 입력변수가 아니므로,
            # cursor.execuet("CREATE DATABASE %s",("dbNmae",)) 형태로 사용할 수 없음.
            # 그래서 sql.format() 형태로 string에서 직접변환함. sql injection 방지를 위해 escape_string()함.
            # data 인자가 1개일 경우 tuple ("1",) 로 써야함. (1) -> 1, (1,) -> (1,) 로 인식함.
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

    def _escStr(self, s):
        return self.dbCon.escape_string(s).decode('utf-8')

    def isExistDB(self, dbName):
        logger.debug(
            "Checking the existence of the database [%s]", self._escStr(dbName))

        sql = """Show databases like '{db}';""".format(db=self._escStr(dbName))

        return len(self._sendQuery(sql)) > 0

    def makeDB(self, dbName):
        if(not self.isExistDB(dbName)):
            logger.debug("Cannot find the database [%s]", self._escStr(dbName))
            logger.debug("Creating the database [%s]", self._escStr(dbName))

            sql = """CREATE DATABASE IF NOT EXISTS {db};""".format(
                db=self._escStr(dbName))
            return self._sendQuery(sql) != None
        else:
            logger.debug("The database [%s] exists", self._escStr(dbName))
            return False

    def deleteDB(self, dbName):
        if(self.isExistDB(dbName)):
            logger.debug("Deleting the database [%s]", self._escStr(dbName))

            sql = """DROP DATABASE IF EXISTS {db};""".format(
                db=self._escStr(dbName))

            return self._sendQuery(sql) != None
        else:
            logger.debug(
                "Cannot find the database [%s] and thus cannot delete it", self._escStr(dbName))
            return False

    def isExistTB(self, dbName, tbName):

        if (self.isExistDB(dbName)):
            logger.debug(
                "Checking the existence of the user table [%s] in the database [%s]", self._escStr(tbName), self._escStr(dbName))

            sql = """Show tables in {db} like '{tb}';""".format(
                db=self._escStr(dbName), tb=self._escStr(tbName))

            return len(self._sendQuery(sql)) > 0
        else:
            logger.debug(
                "There is no database [%s]", self.self._escStr(dbName))
            return False

    def makeTB(self):
        # design to rewrite the method in the child class
        pass

    def deleteTB(self, dbName, tbName):
        if(self.isExistTB(dbName, tbName)):
            logger.debug(
                "Deleting the user table [%s] in the database [%s]", self._escStr(tbName), self._escStr(dbName))

            sql = """DROP TABLE IF EXISTS {db}.{tb};""".format(
                db=self._escStr(dbName), tb=self._escStr(tbName))
            return self._sendQuery(sql) != None
        else:
            logger.debug(
                "Cannot find the table [%s] in the database [%s] and thus cannot delete it", self._escStr(tbName), self._escStr(dbName))
            return False

    def _where(self, dic):
        # make [ where key1=%({key1})s and key2 = %({key2})s; ]
        # sql = """select * from {db}.{tb} where loginID = %(loginID)s and passwd= %(passwd)s and privilege=%(privilige)s"""
        wh_Org = """ where """
        wh = wh_Org
        for key, value in dic.items():
            if not value == "":
                if len(wh) > len(wh_Org):
                    wh = wh + " and "

                wh = wh + """{key}=%({key})s""".format(key=key)

        return wh + ";" if len(wh) > len(wh_Org) else ";"

    def _values(self, dic):
        # make [ (key1, key2, key3) values (%({key1})s, %({key2})s, %({key3})s); ]
        # sql = """insert {db}.{tb} (loginID, passwd, privilege) values (%(loginID), %(passwd)s, %(privilige))"""
        val_Org = " ( "
        keys = val_Org
        vals = val_Org
        for key, value in dic.items():
            if not value == "":
                if len(keys) > len(val_Org):
                    keys = keys + ", "
                    vals = vals + ", "

                keys = keys + """{key}""".format(key=key)
                vals = vals + """%({key})s""".format(key=key)

        if len(keys) > len(val_Org):
            return keys + " ) values " + vals + " );"

        else:
            logger.error("no data to be updated")
            return

    def _set(self, dic):
        # make [ set key1 = '%({key1})s', key2 = '%({key2})s']
        # sql = """update {db}.{tb} set passwd='%({pwd})s', privilege=%({pr})s where loginID='%({loginID})s'; """
        se_Org = " set "
        se = se_Org

        for key, value in dic.items():
            if not value == "":
                if len(se) > len(se_Org):
                    se = se + " , "

                se = se + """{key}=%({key})s""".format(key=key)

        return se if len(se) > len(se_Org) else ""


class HandleUserDB(HandleDB):

    def __init__(self, dbHost, dbUser, dbPasswd, dbName, tbName):
        logger.debug("Initializing HandleUserDB Class")
        super().__init__(dbHost, dbUser, dbPasswd)

        self.dbName = self._escStr(dbName)
        self.tbName = self._escStr(tbName)

        if(not self.isExistDB(self.dbName)):
            self.makeDB(self.dbName)

        if(not self.isExistTB(self.dbName, self.tbName)):
            self.makeTB()

    def __del__(self):
        logger.debug("Deleting HandleUserDB Class")
        super().__del__()

    def makeTB(self):
        if (self.isExistDB(self.dbName)):
            if(not self.isExistTB(self.dbName, self.tbName)):
                logger.debug(
                    "Cannot find the user table [%s] in the database [%s]", self.tbName, self.dbName)
                logger.debug(
                    "Creating the user table [%s] in the database [%s]", self.tbName, self.dbName)

                sql = """CREATE TABLE IF NOT EXISTS {db}.{tb} (
                        idUser 		int 		unsigned NOT NULL AUTO_INCREMENT,
                        loginID  	varchar(32) NOT NULL,
                        passwd 	    varchar(64) NOT NULL,
                        privilege	boolean     DEFAULT false,
                        deleteflag	boolean     DEFAULT false,
                        PRIMARY KEY (idUser)
                        ) DEFAULT CHARSET=utf8;""".format(db=self.dbName, tb=self.tbName)

                return self._sendQuery(sql) != None
            else:
                logger.debug(
                    "The user table [%s] in database [%s] exists", self.tbName, self.dbName)
                return False
        else:
            logger.debug(
                "There is no database [%s]", self.dbName)
            return False

    def isExistUser(self, userInfo):
        logger.debug(
            "Checking the existence of the user in the user table [%s] of the database [%s]", self.tbName, self.dbName)

        # need space between table name and where
        sql = """select * from {db}.{tb}""".format(
            db=self.dbName, tb=self.tbName) + " " + self._where(userInfo)

        return len(self._sendQuery(sql, userInfo)) > 0

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

            return True if self._sendQuery(sql, data=userInfo, mode="DML") == None else False

    def rmUserAccount(self, loginID):
        if (self.isExistLoginID(loginID)):
            logger.debug(
                "Removing the user ID [%s] from the user table [%s] in the database [%s]", loginID, self.tbName, self.dbName)

            sql = """delete from {db}.{tb}""".format(
                db=self.dbName, tb=self.tbName) + self._where({'loginID': loginID})

            return True if self._sendQuery(sql, data={'loginID': loginID}, mode="DML") == None else False
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

            rlt = self._sendQuery(sql, data={'loginID': loginID})
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

            return True if self._sendQuery(sql, data=userInfo, mode="DML") == None else False
        else:
            logger.error("Your user ID [%s] doesnot exist in the user table [%s] of the database [%s] and thus cannot be updated",
                         userInfo['loginID'], self.tbName, self.dbName)
            return False


class HandleMusicDB(HandleDB):

    def __init__(self, dbHost, dbUser, dbPasswd, dbName, tbName):
        logger.debug("Initializing HandleMusicDB Class")
        super().__init__(dbHost, dbUser, dbPasswd)

        self.dbName = self._escStr(dbName)
        self.tbName = self._escStr(tbName)

        if(not self.isExistDB(self.dbName)):
            self.makeDB(self.dbName)

        if(not self.isExistTB(self.dbName, self.tbName)):
            self.makeTB()

    def __del__(self):
        logger.debug("Deleting HandleMusicDB Class")
        super().__del__()

    def makeTB(self):
        if (self.isExistDB(self.dbName)):
            if(not self.isExistTB(self.dbName, self.tbName)):
                logger.debug(
                    "Cannot find the music table [%s] in the database [%s]", self.tbName, self.dbName)
                logger.debug(
                    "Creating the music table [%s] in the database [%s]", self.tbName, self.dbName)

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
                        ) DEFAULT CHARSET=utf8;""".format(db=self.dbName, tb=self.tbName)

                return self._sendQuery(sql) != None
            else:
                logger.debug(
                    "The user table [%s] in database [%s] exists", self.tbName, self.dbName)
                return False
        else:
            logger.debug(
                "There is no database [%s]", self.dbName)
            return False

    def isExistMusic(self, musicInfo):
        logger.debug(
            "Checking the existence of the music [%s] in the music table [%s] of the database [%s]", musicInfo, self.tbName, self.dbName)

        # need space between table name and where
        sql = """select * from {db}.{tb}""".format(
            db=self.dbName, tb=self.tbName) + " " + self._where(musicInfo)

        return len(self._sendQuery(sql, musicInfo)) > 0

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

            return True if self._sendQuery(sql, data=musicInfo, mode="DML") == None else False

    def rmMusicRecordArtistTitle(self, artist, title):

        if (self.isExistMusicArtistTitle(artist, title)):
            logger.debug(
                "Removing the muisc info record having title [%s] and artist [%s] from the music table [%s] in the database [%s]",
                title, artist, self.tbName, self.dbName)

            sql = """delete from {db}.{tb}""".format(
                db=self.dbName, tb=self.tbName) + self._where({'title': title, 'artist': artist})

            return True if self._sendQuery(sql, data={'title': title, 'artist': artist}, mode="DML") == None else False
        else:
            logger.error(
                "The music info record having title [%s] and artist [%s] doesnot exist in the music table [%s] of the database [%s] and thus cannot be deleted",
                title, artist, self.tbName, self.dbName)
            return False

    def getMusicRecordArtistTitle(self, artist, title):
        if (self.isExistMusicArtistTitle(artist, title)):
            logger.debug(
                "Getting the music info record having title [%s] and artist [%s] from the music table [%s] in the database [%s]",
                title, artist, self.tbName, self.dbName)
            sql = """select * from {db}.{tb}""".format(
                db=self.dbName, tb=self.tbName) + self._where({'title': title, 'artist': artist})

            rlt = self._sendQuery(sql, data={'title': title, 'artist': artist})
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

            return True if self._sendQuery(sql, data=musicInfo, mode="DML") == None else False
        else:
            logger.error("The music info record having title [%s] and artist [%s] doesnot exist in the music table [%s] of the database [%s] and thus cannot be updated",
                         musicInfo['artist'], musicInfo['title'], self.tbName, self.dbName)
            return False


class HandleFile:
    def __init__(self):
        logger.debug("Initializing HandleFile Class")

    def __del__(self):
        logger.debug("Deleting HandleFile Class")

    def mkDir(self, strDir):
        try:
            pathlib.Path(strDir).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error("%s. Error in mkDir() [%s]", e, strDir)
            raise

    def rmDir(self, strDir):
        try:
            shutil.rmtree(strDir)
        except Exception as e:
            logger.error("%s. Error in rmDir() [%s]", e, strDir)
            raise

    def mkFileList(self, fileList):
        def walk(path):
            for p in pathlib.Path(path).iterdir():
                if p.is_dir():
                    yield from walk(p)
                    continue
                yield p.resolve()

        result = []
        for ff in fileList if type(fileList) is list else [fileList]:
            hPath = pathlib.Path(ff)
            if(hPath.is_dir()):
                logger.info("%s is directory. Walk into the directory " % ff)
                [result.append(str(x)) for x in walk(ff)]
            else:
                result.append(str(hPath.resolve()))
        return result

    def svFile(self, fName, data, binMode=True):
        try:
            if binMode:
                pathlib.Path(fName).write_bytes(data)
            else:
                pathlib.Path(fName).write_text(data)
        except Exception as e:
            logger.error("%s. Error in svFile [%s]", e, fName)
            raise

    def mvFile(self, src, tgt):
        try:
            pathlib.Path(src).rename(tgt)
        except Exception as e:
            logger.error("%s. Error in mvFile [%s] to [%s] ", e, src, tgt)
            raise


class HandleTag:
    def __init__(self):
        logger.debug("Initializing HandleTag Class")
        self.id3Frames = {'title': 'TIT2', 'artist': 'TPE1', 'album': 'TALB', 'sdate': 'TDRC',
                          'genre': 'TCON', 'filename': 'PATH', 'imgname': 'APIC', 'lyricname': 'USLT'}
        self._tmpImage = '_tmpImage'
        self._tmpLyric = '_tmpLyric'

    def __del__(self):
        logger.debug("Deleting HandleTag Class")

    def getTag(self, fName):
        # All strings are unicode in python3. we don't need to decode string anymore.
        logger.debug("Gathering ID3 Tag of [%s]", fName)
        result = {}
        try:
            # music 파일이 아니면 로딩시에 에러 발생. file doesn't start with an ID3 tag.
            # 에러 발생시 return None 하므로 return 값 확인에서 None이 아니면 tagResults에 넣음.
            tagList = ID3(fName).items()

            for col, frame in self.id3Frames.items():
                for key, value in tagList:
                    if frame in key:
                        result[col] = self._tagParsing(frame, value)
                        tagList.remove((key, value))
                        break

            return result

        except Exception as e:
            # If file has no id3 head, ruturn None
            logger.debug(
                "%s. Error occured during loading tag of [%s]. It may be not music file", e, fName)
            return None

#     result['currentrank'] = 9999
#     result['favor'] = 0
#     result['deleteflag'] = False

#     return result

        # title		varchar(256),
        # artist 		varchar(256),
        # album 		varchar(256),
        # sdate 		date,
        # genre 		varchar(32),
        # filename 	varchar(256),
        # imgname 	varchar(256),
        # lyricname 	varchar(256),
        # currentrank	int		unsigned,
        # favor		int		unsigned,
        # deleteflag	int		unsigned,

    def _tagParsing(self, key, value):
        if key == 'APIC':
            # save album image and return tmporary filename
            HandleFile().svFile(self._tmpImage, value.data, binMode=True)
            return self._tmpImage
        elif key == 'USLT':
            # save lyric and return tmporary filename
            HandleFile().svFile(self._tmpLyric, value.text, binMode=False)
            return self._tmpLyric
        else:
            # tilte TIT2, artist TPE1, album TALB, genre TCON
            return value.text[0]


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
    # logger.setLevel(logging.DEBUG)

    # # TEST: hUserDB
    # logger.setLevel(logging.INFO)
    # hUserDB = HandleUserDB(DB_HOST, DB_USER, DB_PASSWD, DB_NAME, USER_TB_NAME)
    # userInfo = {'loginID': DB_USER, 'passwd': DB_PASSWD, 'privilege': True}
    # test_hUserDB(hUserDB, userInfo)

    # # TEST : hMusicDB
    # logger.setLevel(logging.INFO)
    # hMusicDB = HandleMusicDB(DB_HOST, DB_USER, DB_PASSWD, DB_NAME, TEMP_UID)
    # musicInfo = {'title': '노래', 'artist': '아이유', 'album': '발라드', 'sdate': 20211011, 'genre': '발라드', 'filename': 'file_here',
    #              'imgname': 'img_here', 'lyricname': 'lyric_here', 'currentrank': 999, 'favor': 1, 'deleteflag': 0}
    # test_hMusicDB(hMusicDB, musicInfo)

    hFile = HandleFile()
    hTag = HandleTag()

    fList = hFile.mkFileList("imsi2")

    i = 0
    for ff in fList:
        i = i + 1
        print(i, end=" : ")
        print(pathlib.PurePath(ff).name, end=" : ")
        print(hTag.getTag(ff))

    hFile.mvFile('_tmpImage', 'Img_' + pathlib.PurePath(ff).stem+".jpg")

    # # sql injection test
    # hUserDB = HandleUserDB(DB_HOST, DB_USER, DB_PASSWD, DB_NAME, USER_TB_NAME)
    # showall_test(hUserDB, """' or 1=1 --'""")
    # # showall_test1(hUserDB, """' or 1=1--'""")
    # showall_test2(hUserDB, """' or 1=1--'""")
