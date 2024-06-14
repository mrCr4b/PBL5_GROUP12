import cv2
import torch
import sqlalchemy
from sqlalchemy import create_engine, Column, String, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from collections import defaultdict
from sqlalchemy import Boolean, DateTime, Integer, LargeBinary
from datetime import datetime, timedelta
from sqlalchemy.orm import declarative_base
from flask import Flask, render_template
import serial
from sqlalchemy import Boolean, DateTime, Integer, LargeBinary
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Api, Resource, fields, marshal_with
from flask import Flask, redirect, url_for, render_template, request, session
import base64


app = Flask(__name__)
api = Api(app)
app.secret_key = 'hola'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root@localhost/parkpal'
#app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root@192.168.63.40:3306/parkpal'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit

#arduinoVao = serial.Serial('COM6', 38400) # Adjust the port as needed
#arduinoRa = serial.Serial('COM6', 38400) # Adjust the port as needed

db = SQLAlchemy(app)

class car_plates(db.Model):
    id = db.Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    user_id = db.Column(Integer, nullable=False)
    plate_number = db.Column(db.String(50), nullable=False)
    
class parking(db.Model):
    id = db.Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    id_user = db.Column(Integer, nullable=False)
    car_number = db.Column(db.String(50), nullable=False)
    time_in = db.Column(DateTime, nullable=True)
    time_out = db.Column(DateTime, nullable=True)
    image_in = db.Column(LargeBinary, nullable=True)
    image_out = db.Column(LargeBinary, nullable=True)
    

    
class CamVao(Resource):
    def post(self):
        bien_so = request.form['bien_so']
        anh_vao = request.files['image'].read()
        
        print(f'Xe vao: {bien_so}')
        print(f'Anh: {len(anh_vao)} bytes')
        
        co_ton_tai_bien_so = car_plates.query.filter_by(plate_number=bien_so).first()
                
        da_co_trong_bang_do_xe_chua = parking.query.filter_by(car_number=bien_so).filter(parking.time_out.is_(None)).first()
        
        so_luong_xe_dang_do = parking.query.with_entities(func.count(parking.id)).filter(parking.time_out.is_(None)).scalar()
        
        if co_ton_tai_bien_so and da_co_trong_bang_do_xe_chua:
            return {"ket_qua": "xe_da_co_trong_bai"}
                    
        if co_ton_tai_bien_so and not da_co_trong_bang_do_xe_chua:
            # Thêm biển số vào bảng do_xe
            id_tk = co_ton_tai_bien_so.user_id
            new_parking = parking(id_user=id_tk, car_number=bien_so, time_in=datetime.utcnow() + timedelta(hours=7),image_in=anh_vao)

            # Add the new product to the database session
            db.session.add(new_parking)
                
            # Commit the transaction to save the changes to the database
            db.session.commit()
                
            #arduinoVao.write(b'1')
                
            return {"ket_qua": "xe_chua_o_trong_bai"}
        
            
class CamRa(Resource):
    def post(self):
        bien_so = request.form['bien_so']
        anh_ra = request.files['image'].read()
        
        print(f'Xe ra: {bien_so}')
        print(f'Anh: {len(anh_ra)} bytes')
                    
        da_co_trong_bang_do_xe_chua = parking.query.filter_by(car_number=bien_so).filter(parking.time_out.is_(None)).first()
        
        if da_co_trong_bang_do_xe_chua:
            da_co_trong_bang_do_xe_chua.time_out = datetime.utcnow() + timedelta(hours=7)
            da_co_trong_bang_do_xe_chua.image_out = anh_ra
        
            # Commit the changes to the database
            db.session.commit()
            
            #arduinoRa.write(b'1')
            
            return {"ket_qua": "xe_ra_khoi_bai_thanh_cong"}
        
api.add_resource(CamVao, "/camvao")
api.add_resource(CamRa, "/camra")
    
if __name__ == "__main__":
    app.run(host='192.168.63.40', port=5003, debug=True)

