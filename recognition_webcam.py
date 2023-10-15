import cv2
import numpy as np
import os
import pickle
import asyncio
import sys
import firestore

import whatsapp
from whatsapp import enviar_mensagem

from helper_functions import resize_video


threshold = 98

max_width = 800

face_names = {}
with open("face_names.pickle", "rb") as f:
    original_labels = pickle.load(f)
    face_names = {v: k for k, v in original_labels.items()}

array_predicoes = []

def recognize_faces(network,  orig_frame, face_names, threshold, conf_min=0.7):
    face_classifier = cv2.face.LBPHFaceRecognizer_create()
    face_classifier.read("lbph_classifier.yml")

    frame = orig_frame.copy()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    (h, w) = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 1.0, (300, 300), (104.0, 117.0, 123.0))
    network.setInput(blob)
    detections = network.forward()

    for i in range(0, detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        if confidence > conf_min:
            bbox = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (start_x, start_y, end_x, end_y) = bbox.astype("int")

            if (start_x<0 or start_y<0 or end_x > w or end_y > h):
                continue

            face_roi = gray[start_y:end_y,start_x:end_x]
            face_roi = cv2.resize(face_roi, (90, 120))
            prediction, conf = face_classifier.predict(face_roi)

            cv2.rectangle(frame, (start_x, start_y), (end_x, end_y), (0, 255, 0), 2)
            nome_formatado = face_names[prediction].split("-")[0]
            pred_name = nome_formatado if conf <= threshold else "Not identified"

            if (conf > 100):
                text = "Nao identificado"
            else:
                # enviar mesagem caso o cara nao tenha sido reconhecido
                if prediction not in array_predicoes:
                    mandar_mensagem(orig_frame, face_names[prediction])
                    array_predicoes.append(prediction)

                text = "{} -> {:.4f}".format(pred_name, conf)

            cv2.putText(frame, text, (start_x, start_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            # face = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
    return frame

def mandar_mensagem(frame, nome):
    nome_arquivo = f"print-{nome}.jpg"
    cv2.imwrite(nome_arquivo, frame)
    firestore.adicionarPrintSuspeito(nome, nome_arquivo)
    link_imagem = firestore.pegar_print(nome)
    cpf_foragido = nome.split("-")[1]
    foragido = pegar_foragido(cpf_foragido)
    whatsapp.enviar_mensagem(foragido, link_imagem)

def pegar_foragido(cpf):
    return firestore.pegarForagidoPeloCpf(cpf)

network = cv2.dnn.readNetFromCaffe("deploy.prototxt.txt", "res10_300x300_ssd_iter_140000.caffemodel")