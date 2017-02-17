# -*- coding: utf-8 -*- 
import time
from ctypes import *
from io import BytesIO
import platform
import logging
import os

logging.basicConfig(level=logging.DEBUG)

BASEPATH=os.path.split(os.path.realpath(__file__))[0]

def play(filename):
    import pygame
    pygame.mixer.init(frequency=16000)
    pygame.mixer.music.load(filename)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy() == True:
        continue



def getWaveData(_tmpFile = 'iflytek01.wav'):
    with open(_tmpFile,'rb') as f:
        return f.read()


def convDataToPointer(wav_data):
    tmpBytes = BytesIO()
    f_size = tmpBytes.write(wav_data)
    array = ( c_byte * f_size)()
    tmpBytes.seek(0,0)
    tmpBytes.readinto(array)
    return array


def speech_to_text(waveData):
    

    plat = platform.architecture()
    if plat[0] == '32bit':
        cur = cdll.LoadLibrary(BASEPATH + '/x86/libmsc.so')
    else:
        cur = cdll.LoadLibrary(BASEPATH + '/x64/libmsc.so')
       

    MSPLogin = cur.MSPLogin
    QISRSessionBegin = cur.QISRSessionBegin
    QISRAudioWrite = cur.QISRAudioWrite
    QISRGetResult = cur.QISRGetResult
    QISRGetResult.restype = c_void_p
    QISRSessionEnd = cur.QISRSessionEnd

    p_pcm = convDataToPointer(waveData)
    pcm_size = sizeof(p_pcm)
    
    ret_c = c_int(0)
    ret = 0

    ep_stat = c_int(0)
    rec_stat = c_int(0)

    ret = MSPLogin(None,None,'appid = 539feff8, work_dir = .') 
    if ret != 0:
        logging.error("MSPLogin failed, error code: " + ret);
        return


    logging.info("开始语音听写 ...")
    session_begin_params = "sub = iat, domain = iat, language = zh_cn, accent = mandarin, sample_rate = 16000, result_type = plain, result_encoding = utf8";
    sessionID = QISRSessionBegin(None,session_begin_params, byref(ret_c));
    if ret_c.value != 0 :
        logging.error("QISRSessionBegin failed, error code: " + ret_c.value);
        return

    pcm_count = 0
    len = 10 * 640; #每次写入200ms音频(16k，16bit)：1帧音频20ms，10帧=200ms。16k采样率的16位音频，一帧的大小为640Byte
    while True:
        if pcm_size < 2 * len:
            len = pcm_size
        if len <= 0 :
            break

        aud_stat = 2
        if 0 == pcm_count:
            aud_stat = 1
            
        ret = QISRAudioWrite(sessionID, byref(p_pcm,pcm_count),len, aud_stat, byref(ep_stat), byref(rec_stat));
        if ret != 0:
            logging.error("QISRAudioWrite failed, error code: " + ret);
            break

        pcm_count += len
        pcm_size  -= len

        if ep_stat.value == 3:
            break
        time.sleep(.1)
 

    ret = QISRAudioWrite(sessionID, None,0, 4, byref(ep_stat), byref(rec_stat));
    if ret != 0:
        logging.error("QISRAudioWrite failed, error code: " + ret);

    error_c = c_int(0)
    text_finish = ""
    while  rec_stat.value != 5:
        x = QISRGetResult(sessionID, byref(rec_stat), 0, error_c);
        if x!=None:
            num = 0
            while True:
                if (c_char).from_address(x+num).value != c_char('\x00').value:
                    num += 1
                else:
                    break
            text = (c_char * num).from_address(x)
            text_finish += text.value

        time.sleep(.1)
    logging.debug(text_finish)
    logging.info('合成完成！')
    ret = QISRSessionEnd(sessionID, "Normal");
    if ret != 0:
        logging.error("QTTSTextPut failed, error code: " + ret);

    return text_finish


if __name__ == '__main__':
    speech_to_text(getWaveData('xx.wav'))
