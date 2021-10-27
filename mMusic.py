#!/Users/taehyunghwang/pyWorks/mMusic/.venv/bin/python
# -*- coding: utf-8 -*-
# ver 0.1 : release 19.08.07
# ver 0.2 : support ranking  based on melon top 100 chart
# ver 0.3 : support updating database based on music in the directory
# ver 0.4 : [bug fix] change handling escape characters
# ver 0.5 : change to python3 and make class

import shutil
import pathlib

import logging
import logging.handlers
import MySQLdb
from mutagen.id3 import ID3


class HandleDB:

    def __init__(self, dbInfo={}):
        logger.debug("Initializing HandleDB Class with dbInfo [%s]", dbInfo)
        super(HandleDB, self).__init__()
        self.connectDB(dbInfo)

    def __del__(self):
        logger.debug("Deleting HandleDB Class")
        self.closeDB()

    def connectDB(self, dbInfo):
        if len(dbInfo) >= 3:
            logger.debug("Connecting to the database sever")
            try:
                self.dbCon = MySQLdb.connect(
                    host=dbInfo['dbHost'], user=dbInfo['dbUser'], passwd=dbInfo['dbPasswd'], charset='utf8')
                logger.debug("Success to connect to the database sever")
            except Exception as e:
                logger.error(
                    "Fail to connect to the database sever. Error message : %s.", e)
                raise
        else:
            logger.debug(
                "Insufficient dbInfo [%s]. Fill dbInfo and use connectDB()", dbInfo)

    def closeDB(self):

        if 'dbCon' in dir(self):
            logger.debug("Closing DB Connection ")
            self.dbCon.close()
            del(self.dbCon)

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

    def setDB(self, dbName):
        if not dbName == '':
            self.dbName = self._escStr(dbName)
            self.makeDB(self.dbName)
        else:
            logger.debug(
                "[setDB] dbName is not defined. Define dbName and use setDB()")

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

    def __init__(self, dbInfo={}, dbName='', tbName=''):
        logger.debug("Initializing HandleUserDB Class")
        super(HandleUserDB, self).__init__(dbInfo)

        self.setDB(dbName)
        self.setTable(tbName)

    def __del__(self):
        logger.debug("Deleting HandleUserDB Class")
        super(HandleUserDB, self).__del__()

    def setTable(self, tbName):
        if 'dbName' in dir(self):
            if not tbName == '':
                self.tbName = self._escStr(tbName)
                self.makeTB()
            else:
                logger.debug(
                    "[setTable] tbName is not defined. Define tbName first and use setTable()")
        else:
            logger.debug(
                "[setTable] dbName is not defined. Define dbName first and use setDB()")

    def makeTB(self):
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

    def __init__(self, dbInfo={}, dbName='', tbName=''):
        logger.debug("Initializing HandleMusicDB Class")
        super(HandleMusicDB, self).__init__(dbInfo)

        self.setDB(dbName)
        self.setTable(tbName)

    def __del__(self):
        logger.debug("Deleting HandleMusicDB Class")
        super(HandleMusicDB, self).__del__()

    def setTable(self, tbName):
        if 'dbName' in dir(self):
            if not tbName == '':
                self.tbName = self._escStr(tbName)
                self.makeTB()
            else:
                logger.debug(
                    "[setTable] tbName is not defined. Define tbName first and use setTable()")
        else:
            logger.debug(
                "[setTable] dbName is not defined. Define dbName first and use setDB()")

    def makeTB(self):
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


class HandleMusicTag:

    def __init__(self):
        logger.debug("Initializing HandleMusicTag Class")
        super(HandleMusicTag, self).__init__()
        self.id3Frames = {'title': 'TIT2', 'artist': 'TPE1', 'album': 'TALB', 'sdate': 'TDRC',
                          'genre': 'TCON', 'filename': 'PATH', 'imgname': 'APIC', 'lyricname': 'USLT'}
        self._tmpImage = '_tmpImage'
        self._tmpLyric = '_tmpLyric'

    def __del__(self):
        logger.debug("Deleting HandleMusicTag Class")

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
                        result[col] = self._tagParsing(frame, value, fName)
                        tagList.remove((key, value))
                        break

            return result

        except Exception as e:
            # If file has no id3 head, ruturn None
            logger.debug(
                "%s. Error occured during loading tag of [%s]. It may be not music file", e, fName)
            return None

    def _tagParsing(self, key, value, fName):
        if key == 'APIC':
            # save album image and return tmporary filename
            imgPath = pathlib.PurePath(fName).parent.joinpath(self._tmpImage)
            HandleFile().svFile(imgPath, value.data, binMode=True)
            return imgPath
        elif key == 'USLT':
            # save lyric and return tmporary filename
            lyrPath = pathlib.PurePath(fName).parent.joinpath(self._tmpLyric)
            HandleFile().svFile(lyrPath, value.text, binMode=False)
            return lyrPath
        else:
            # tilte TIT2, artist TPE1, album TALB, genre TCON
            return value.text[0]


class HandleFile:
    def __init__(self):
        logger.debug("Initializing HandleFile Class")
        super(HandleFile, self).__init__()

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


class HandleMusic(HandleMusicDB, HandleMusicTag, HandleFile):

    # userID를 인수로 받아서 그 이름의 music table을 만들고
    # 파일/디렉토리를 인수로 받아서 music tag를 얻어서
    # music tabel에 입력하고 target directory 로 옮김

    def __init__(self, dbInfo={}, dbName='', tbName=''):
        logger.debug(
            "Initializing HandleMusic Class with dbInfo [%s], dbName [%s], tbName[%s]", dbInfo, dbName, tbName)
        super(HandleMusic, self).__init__(dbInfo, dbName, tbName)
        pass

    def __del__(self):
        logger.debug("Deleting HandleMusic Class")
        super(HandleMusic, self).__del__()

    def mkMusicInfo(self, fileList):
        # flist 입력으로 tag Info list를 작성함.
        logger.debug("Making Muisc Info .. ")

        result = []

        for ff in self.mkFileList(fileList):
            tmpDic = self.getTag(ff)

            if not tmpDic == None:
                fParent = pathlib.PurePath(ff).parent
                fName = pathlib.PurePath(ff).name
                fStem = pathlib.PurePath(ff).stem

                if not 'title' in tmpDic.keys():
                    tmpDic['title'] = fStem

                tmpDic['filename'] = fName

                if 'imgname' in tmpDic.keys():
                    imgname = fParent.joinpath('CoverImg_' + fStem + '.jpg')
                    self.mvFile(tmpDic['imgname'], imgname)
                    tmpDic['imgname'] = str(imgname)

                if 'lyricname' in tmpDic.keys():
                    lyricname = fParent.joinpath('Lyric_' + fStem + '.txt')
                    self.mvFile(tmpDic['lyricname'], lyricname)
                    tmpDic['lyricname'] = str(lyricname)

                tmpDic['currentrank'] = 9999
                tmpDic['favor'] = 0
                tmpDic['deleteflag'] = False

                result.append(tmpDic)

        return result

        # def addMusic(dbCon, dbName, homeDir, userInfo, musicList):
        #     logger.debug("Adding musics list ---")

        #     updateMusicDB(dbCon, dbName, userInfo['uid'], [
        #                   os.path.join(homeDir, userInfo['uid']), ])
        #     insertMusicDB(dbCon, dbName, userInfo['uid'], os.path.join(
        #         homeDir, userInfo['uid']), musicList)

        #     return True

        # def insertMusicDB(dbCon, dbName, musicTB, dstDir, musicList):
        #     logger.info("inserting music information into database .....")

        #     for ff in makeMusicList(musicList):
        #         tagToUTF8(ff)
        #         tag = getTag(ff)

        #         if (isInMusicDB_ArtistTitle(dbCon, dbName, musicTB, tag)):
        #             # ----
        #             logger.info(
        #                 "[Skip] {fn} already exists ................. [Skip]".format(fn=ff))
        #         else:
        #             logger.info(
        #                 "[Move] {fn} is moving to {dr} ............... [Ok]".format(fn=ff, dr=dstDir))

        #             insertMusicRecord(dbCon, dbName, musicTB, tag)
        #             shutil.move(ff, dstDir)

        # def updateMusicDB(dbCon, dbName, musicTB, musicDir):  # musicDir should be list
        #     logger.info("Updating Database .....")
        #     music directory에 없는 것은 DB에서 삭제하고, 있는 것들은 favor +1

        #     setDeleteFlag(dbCon, dbName, musicTB)

        #     for ff in makeMusicList(musicDir):
        #         tag = getTag(ff)
        #         if (isInMusicDB_ArtistTitle(dbCon, dbName, musicTB, tag)):
        #             unsetDeleteFlag(dbCon, dbName, musicTB, tag)
        #             increaseFavor(dbCon, dbName, musicTB, tag)

        #     return deleteMusicRecord(dbCon, dbName, musicTB)

        # def setDeleteFlag(dbCon, dbName, musicTB):
        #     logger.debug("Setting delete-flag of all music to on")
        #     sql = """update {db}.{tb} set deleteflag=True"""
        #     sql = sql.format(db=dbName, tb=musicTB)

        #     return sendQuery(dbCon, sql, mode="DML")

        # def unsetDeleteFlag(dbCon, dbName, musicTB, tag):
        #     logger.debug("Setting delete-flag of all music to off")
        #     sql = """update {db}.{tb} set deleteflag=False where title = "{ti}" and artist="{ar}" """
        #     sql = sql.format(db=dbName, tb=musicTB, ti=simplify(
        #         tag['title']), ar=simplify(tag['artist']))

        #     return sendQuery(dbCon, sql, mode="DML")

        # def increaseFavor(dbCon, dbName, musicTB, tag):
        #     logger.debug("Increasing favorite number of music")
        #     sql = """update {db}.{tb} set favor=favor+1 where title = "{ti}" and artist="{ar}" """
        #     sql = sql.format(db=dbName, tb=musicTB, ti=simplify(
        #         tag['title']), ar=simplify(tag['artist']))

        #     return sendQuery(dbCon, sql, mode="DML")

        # def deleteMusicRecord(dbCon, dbName, musicTB):
        #     logger.debug("Deleting music records having on delete-flag ")
        #     sql = """delete from {db}.{tb} where deleteflag=True"""
        #     sql = sql.format(db=dbName, tb=musicTB)

        #     return sendQuery(dbCon, sql, mode="DML")


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


def test_hMusic(hd, dbInfo, dbName, tbName):
    print('connectDB -------------- ')
    hd.connectDB(dbInfo)
    print('setDB -------------- ')
    hd.setDB(dbName)
    print('set Table -------------- ')
    hd.setTable(tbName)
    print('print internal variable -------------- ')
    print(hd.id3Frames)
    hd.closeDB()


def test_class():
    print('HandleDB')
    hMusic = HandleDB()
    del(hMusic)
    print('HandleMusicDB')
    hMusic = HandleMusicDB()
    del(hMusic)
    print('HandleMusicTag')
    hMusic = HandleMusicTag()
    del(hMusic)
    print('HandleUserDB')
    hMusic = HandleUserDB()
    del(hMusic)
    print('HandleFile')
    hMusic = HandleFile()
    del(hMusic)
    print('HandleMusic')
    hMusic = HandleMusic()
    print(hMusic.id3Frames)
    del(hMusic)


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

    dbInfo = {'dbHost': DB_HOST, 'dbUser': DB_USER, 'dbPasswd': DB_PASSWD}

    # # TEST: hUserDB
    # logger.setLevel(logging.INFO)
    # hUserDB = HandleUserDB(dbInfo, DB_NAME, USER_TB_NAME)
    # userInfo = {'loginID': DB_USER, 'passwd': DB_PASSWD, 'privilege': True}
    # test_hUserDB(hUserDB, userInfo)

    # # TEST : hMusicDB
    # logger.setLevel(logging.INFO)
    # hMusicDB = HandleMusicDB(dbInfo, DB_NAME, TEMP_UID)
    # musicInfo = {'title': '노래', 'artist': '아이유', 'album': '발라드', 'sdate': 20211011, 'genre': '발라드', 'filename': 'file_here',
    #              'imgname': 'img_here', 'lyricname': 'lyric_here', 'currentrank': 999, 'favor': 1, 'deleteflag': 0}
    # test_hMusicDB(hMusicDB, musicInfo)

    # # TEST : HandleMusic
    # test_hMusic(HandleMusic(), dbInfo, DB_NAME, TEMP_UID)

    # # TEST : make class
    # test_class()

    # hFile = HandleFile()
    # hTag = HandleTag()

    # fList = hFile.mkFileList("imsi2")

    # i = 0
    # for ff in fList:
    #     i = i + 1
    #     print(i, end=" : ")
    #     print(pathlib.PurePath(ff).name, end=" : ")
    #     print(hTag.getTag(ff))

    # hFile.mvFile('_tmpImage', 'Img_' + pathlib.PurePath(ff).stem+".jpg")
    logger.setLevel(logging.INFO)

    hm = HandleMusic()
    print(hm.mkMusicInfo('imsi2'))
