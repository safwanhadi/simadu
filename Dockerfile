FROM python:3.10

#SET ENV
ENV PYTHONDONTWRITERBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV LANG id_ID.UTF-8
ENV LC_ALL id_ID.UTF-8

#INSTALL DEP
RUN apt-get update && apt-get install -y locales
RUN sed -i '/id_ID.UTF-8/s/^# //g' /etc/locale.gen && locale-gen
RUN apt-get update && \
    apt-get install -y locales && \
    sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
    dpkg-reconfigure --frontend=noninteractive locales
RUN pip install --upgrade pip
COPY ./requirements.txt .
RUN pip install -r requirements.txt
COPY . /app

#Set workdir
WORKDIR /app

COPY ./entrypoint.sh /
ENTRYPOINT [ "sh", "./entrypoint.sh" ]