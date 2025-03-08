
#-----------------------------------STAGE-1---------------------------------

#FROM vivekdalsaniya/facelog-env:v0.0 AS builder

#RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

#WORKDIR /app

#RUN git clone https://vivekdalsaniya12:@github.com/vivekdalsaniya12/FaceLog.git /app/FaceLog

#-----------------------------------STAGE-2--------------------------------

FROM facelog:latest

WORKDIR /app
#RUN apt-get update && rm -rf /var/lib/apt/lists/*
#COPY --from=builder /app/FaceLog /app
COPY . .
#RUN pip install -r requirements.txt   
#--no-cache-dir 
RUN python manage.py makemigrations
RUN python manage.py migrate
EXPOSE 8000
ENTRYPOINT ["python", "manage.py"]
CMD ["runserver", "0.0.0.0:8000"]

