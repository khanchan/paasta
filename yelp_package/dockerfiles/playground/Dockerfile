FROM examplecluster_itest_trusty
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update > /dev/null && apt-get install -y openssh-server python-dev docker.io curl vim jq > /dev/null
RUN mkdir -p /var/log/paasta_logs
RUN sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd
RUN mkdir /var/run/sshd
RUN mkdir -p /nail/etc
RUN ln -s /etc/paasta/mesos-cli.json /nail/etc/mesos-cli.json
ADD ./requirements-dev.txt /paasta/requirements-dev.txt
ADD ./requirements.txt /paasta/requirements.txt
RUN pip install pip==9.0.1 virtualenv==15.1.0
RUN pip install -r /paasta/requirements-dev.txt
ADD ./yelp_package/dockerfiles/playground/start.sh /start.sh
