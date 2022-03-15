from datetime import date

import mysql.connector


class MySQL():
    __slots__ = ('dbcon')

    def __init__(self):
        self.dbcon = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="bot"
        )

    def setuser(self, id, username):
        cursor = self.dbcon.cursor()
        cursor.execute(
            f"SELECT ID ,COUNT(*) FROM users WHERE ID={id} GROUP BY ID"
        )
        results = cursor.fetchall()
        row_count = cursor.rowcount
        if row_count == 0:
            cursor.execute(
                "INSERT INTO users (id, username) VALUES (%s, %s)", (id, username)
            )
            self.dbcon.commit()
            print("añadido " + username + " a la tabla usuarios")

    def setguild(self, id, guildName):
        cursor = self.dbcon.cursor()
        cursor.execute(
            f"SELECT ID , COUNT(*) FROM servers WHERE ID={id} GROUP BY ID"
        )
        results = cursor.fetchall()
        row_count = cursor.rowcount
        if row_count == 0:
            cursor.execute(
                "INSERT INTO servers (id,servername) VALUES (%s,%s)", (id, guildName)
            )
            self.dbcon.commit()
            print("añadido " + guildName + " a la tabla servidores")

    # ID	NAME	URL	ARTIST	GENRE	DURATION
    def setsong(self, id, name, url, duration):
        cursor = self.dbcon.cursor()

        cursor.execute(
            "SELECT id, COUNT(*) FROM songs WHERE id=%s GROUP BY id",
            (id,)
        )

        results = cursor.fetchall()
        row_count = cursor.rowcount
        if row_count == 0:
            cursor.execute(
                "INSERT INTO songs (id,name,url,duration) VALUES (%s,%s,%s,%s)", (id, name, url, duration)
            )
            self.dbcon.commit()
            print("añadido " + name + " a la tabla songs")

    def skipSong(self, songid, serverid, userid):
        cursor = self.dbcon.cursor()
        cursor.execute(
            "SELECT songid, serverid, userid, COUNT(*) FROM songstats WHERE songid = %s AND serverid=%s AND userid=%s "
            "GROUP BY songid, serverid, userid",
            (songid, serverid, userid)
        )
        results = cursor.fetchall()
        row_count = cursor.rowcount
        if row_count == 0:
            cursor.execute(
                "INSERT INTO songstats (songid, serverid, userid, timesplayed, timesskipped, firsttime) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (songid, serverid, userid, 0, 1, date.today())
            )
            self.dbcon.commit()
        else:
            cursor.execute(
                "UPDATE songstats SET timesskipped = timesskipped + 1 "
                f"WHERE userid = %s "
                f"AND serverid= %s "
                f"AND songid = %s ",
                (userid, serverid, songid)
            )
            self.dbcon.commit()

    def playSong(self, songid, songName, songURL, duration, serverid, guildname, userid, username=None):
        cursor = self.dbcon.cursor()
        if username is not None:
            self.setuser(userid, username)
        self.setguild(serverid, guildname)
        self.setsong(songid, songName, songURL, duration)
        # Ver si la fila ya existe
        # Por clarificar las columnas son estas:
        # userid songid serverid timesplayed timesskipped firsttimeplayed
        # Las 3 primeros son la PK
        cursor.execute(
            "SELECT songid, serverid, userid, COUNT(*) FROM songstats WHERE songid= %s and serverid= %s and userid=%s "
            "GROUP BY songid, serverid, userid"
            , (songid, serverid, userid)
        )
        results = cursor.fetchall()
        row_count = cursor.rowcount
        print(results)
        if row_count == 0:
            cursor.execute(
                "INSERT INTO songstats (songid,serverid,userid,timesplayed,timesskipped,firsttime)"
                f"VALUES (%s, %s ,%s ,%s ,%s ,%s )",
                (songid, serverid, userid, 1, 0, date.today())

            )
            self.dbcon.commit()
            print(f"Insertado en songstats cancion {songName} para {username} en {serverid}")
        else:
            cursor.execute(
                "UPDATE songstats SET timesplayed = timesplayed + 1 "
                f"WHERE userid = %s "
                f"AND serverid= %s "
                f"AND songid = %s ",
                (userid, serverid, songid)
            )
            self.dbcon.commit()

    def bestSongs(self, serverid, size):
        cursor = self.dbcon.cursor()
        cursor.execute(
            "SELECT songs.url FROM songs "
            "INNER JOIN songstats ON songs.id = songstats.songid "
            "WHERE songstats.serverid = %s "
            "ORDER BY songstats.timesplayed DESC, songstats.timesskipped ASC "
            f"LIMIT {size}",
            (serverid,)
        )
        results = cursor.fetchall()
        return results

    def favSongs(self, userid, size):
        cursor = self.dbcon.cursor()
        cursor.execute(
            "SELECT songs.url FROM songs "
            "INNER JOIN songstats ON songs.id = songstats.songid "
            "WHERE songstats.userid = %s "
            "ORDER BY songstats.timesplayed DESC, songstats.timesskipped ASC "
            f"LIMIT {size}",
            (userid,)
        )
        results = cursor.fetchall()
        return results

    def request(self, params):
        cursor = self.dbcon.cursor()
        try:
            cursor.execute(params)
            return cursor.fetchall()
        except Exception:
            print("La consulta salio mal")
            return "Error"
