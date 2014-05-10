#!/usr/bin/env python

import psycopg2
import datetime
import json
import time
import string
import random

class Node:
	id = None
	identifier = None
	name = None
	created_at = None

	def __init__(self):
		created_at = str(datetime.datetime.now());

	def save(self, cursor):
		if cursor is None:
			return False
		if self.id is not None:
			existing = cursor
			cursor.execute("UPDATE sensors SET name = (%s), updated_at=(%s) WHERE id = (%s)", (self.name, datetime.datetime.utcnow(), self.id))
		else:
			cursor.execute("INSERT INTO sensors(identifier, type, name, created_at, updated_at) VALUES (%s, 'default', %s, %s, %s)", (self.identifier, self.name, datetime.datetime.utcnow(), datetime.datetime.utcnow()))

	def get_configs(self, dbconn):
		return [{'0': int(1 << 8), '1': 1}, {'2': int(1 << 24), '3': int(1 << 16), '4': int(1 << 8), '5': 1}]

	def new_measurement(self, value, cursor, created_at = None):
		if created_at is None:
			created_at = datetime.datetime.utcnow()
		else:
			created_at = datetime.datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
		cursor.execute("INSERT INTO measurements(sensor_id, value, created_at) VALUES (%s, %s, %s)", (int(self.id), value, created_at))
		

	@staticmethod
	def init(json_node):
		if json_node is None:
			return None
		new_node = Node()

		if 'id' in json_node:
			new_node.id = int(json_node['id'])
		if 'name' in json_node:
			new_node.name = json_node['name']
		if 'identifier' in json_node:
			new_node.identifier = json_node['identifier']
		if 'created_at' in json_node:
			new_node.created_at = json_node['created_at']
		else:
			new_node.created_at = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
		return new_node
	
	@staticmethod
	def name_generator(size=6, chars=string.ascii_uppercase + string.digits):
		return ''.join(random.choice(chars) for _ in range(size))

	@staticmethod
	def get_by_identifier(cursor, node_identifier):
		# Query params always with %s, must pass a tuple
		result = cursor.execute("SELECT * FROM nodes WHERE identifier = (%s)", (node_identifier,))
		return Node.init(result)

	@staticmethod
	def get_by_identifier_or_create(cursor, node_identifier):
		node = Node.get_by_identifier(cursor, node_identifier)
		if node is None:
			node = Node.init({'identifier': node_identifier})
			node.save()
		return node

	@staticmethod
	def create_new_measurements(dbconn, json_data):
		if json_data is None:
			return False
		if isinstance(json_data, str):
			json_data = json.loads(json_data)
		if 'payload' in json_data:
			return Node.process_payload(dbconn, json_data['payload'])
			
		return False
	
	@staticmethod
	def process_payload(dbconn, payload):
		slots = payload.split(',')	
		node_identifier = slots[0]
		measurements = slots[1:]
		# The connection will remain open after this
		# The cursor is closed after this block
		with dbconn.cursor() as curs:
			node = Node.get_by_identifier_or_create(curs, node_identifier)
			if node is None:
				print "Node %s doesn't exist" % node_identifier
				return False
			else:
				print "Node %s: %s" % (node.identifier, node.name)
				configs = node.get_configs(dbconn)
				if configs is None:
					return False
				results = []
				for config in configs:
					values = []
					for key, value in config.iteritems():
						if int(key) < len(measurements):
							values = values + [int(measurements[int(key)]) * float(config[key])]
						else:
							break
					results = results + [sum(values)]
				print "Got results: ", results
				for result in results:
					node.new_measurement(result, curs)
				return True
		return False
