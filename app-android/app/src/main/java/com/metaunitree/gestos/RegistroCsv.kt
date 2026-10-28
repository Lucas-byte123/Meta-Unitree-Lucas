package com.metaunitree.gestos

import android.content.Context
import android.util.Log
import java.io.BufferedWriter
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Grava o que o MediaPipe viu em cada frame, como o --log do gesto_webcam.py
 * (mesmas colunas, mais tem_mao). Um arquivo por sessão, em
 * /sdcard/Android/data/com.metaunitree.gestos/files/, para puxar com adb pull.
 */
class RegistroCsv(context: Context) {
    private val pasta = context.getExternalFilesDir(null)
    private var saida: BufferedWriter? = null

    @Synchronized
    fun abrir() {
        fechar()
        val nome = "gestos-" + SimpleDateFormat("yyyyMMdd-HHmmss", Locale.US).format(Date()) + ".csv"
        val arquivo = File(pasta, nome)
        saida = arquivo.bufferedWriter().apply { write("t_ms,gesto,confianca,tem_mao,acao\n") }
        Log.i(TAG, "registrando em ${arquivo.absolutePath}")
    }

    @Synchronized
    fun escrever(l: Leitura, acao: String?) {
        saida?.write("${l.tMs},${l.gesto ?: ""},${"%.3f".format(Locale.US, l.confianca)},${if (l.temMao) 1 else 0},${acao ?: ""}\n")
    }

    @Synchronized
    fun fechar() {
        saida?.close()
        saida = null
    }
}
