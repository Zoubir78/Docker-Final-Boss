# This Makefile is a step by step solution of all the commands you are supposed to run :) 

# .ONESHELL: 
setup: 
	if [ ! -d "docker-final-boss" ]; then \
		pyenv virtualenv 3.11.8 docker-final-boss; \
		pyenv local docker-final-boss; \
		pip install -U pip; \
		pip install -r requirements.txt; \
	fi
