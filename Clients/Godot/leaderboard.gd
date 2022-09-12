# warning-ignore-all:return_value_discarded
extends Node

var server_endpoint = "https://exploitavoid.com/leaderboards/v1/api"
var leaderboard_id = 3
var leaderboard_secret = "656433a96b56132affbfde59758acc44"

signal on_received_entries(was_success, entries)
signal on_received_user_entry(was_success, entry)
signal on_sent_user_value(was_success)

var request_entries_http_request : HTTPRequest
var request_user_entry_http_request : HTTPRequest
var send_user_value_http_request : HTTPRequest

func _ready() -> void:
	request_entries_http_request = HTTPRequest.new()
	add_child(request_entries_http_request)
	request_entries_http_request.connect("request_completed", self, "_handle_received_entries")
	
	request_user_entry_http_request = HTTPRequest.new()
	add_child(request_user_entry_http_request)
	request_user_entry_http_request.connect("request_completed", self, "_handle_received_user_entry")
	
	send_user_value_http_request = HTTPRequest.new()
	add_child(send_user_value_http_request)
	send_user_value_http_request.connect("request_completed", self, "_handle_sent_user_value")
	
func request_entries(start: int, count: int) -> void:
	var url = server_endpoint + "/get_entries?leaderboard_id={0}&start={1}&count={2}"
	url = url.format([leaderboard_id,start,count])
	request_entries_http_request.request(url)
	
func request_user_entry(name: String) -> void:
	var url = server_endpoint + "/get_entries?leaderboard_id={0}&start=1&count=1&search={1}"
	url = url.format([leaderboard_id,name])
	request_user_entry_http_request.request(url)
	
# value can be int or float, therefore no type definition
func send_user_value(name: String, value) -> void:
	var url = server_endpoint + "/update_entry"
	var dict_to_serialize = {
		"name": name,
		"value": value,
		"leaderboard_id": leaderboard_id
	}
	var upload_json = JSON.print(dict_to_serialize)
	var to_hash = "/update_entry" + upload_json + leaderboard_secret;
	var ctx = HashingContext.new()
	ctx.start(HashingContext.HASH_SHA256)
	ctx.update(to_hash.to_utf8())
	var hash_result = ctx.finish()
	send_user_value_http_request.request(url, PoolStringArray(), true, 2, upload_json + hash_result.hex_encode())
	
func _handle_received_entries(_result, response_code, _headers, body) -> void:
	var entries = null
	if response_code == 200:
		entries = parse_json(body.get_string_from_utf8())
	emit_signal("on_received_entries", response_code == 200, entries)

func _handle_received_user_entry(_result, response_code, _headers, body) -> void:
	var entry = null
	if response_code == 200:
		entry = parse_json(body.get_string_from_utf8())
	emit_signal("on_received_user_entry", response_code == 200, entry)
	
func _handle_sent_user_value(_result, response_code, _headers, _body) -> void:
	emit_signal("on_sent_user_value", response_code == 200)
