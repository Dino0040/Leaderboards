extends Node

var server_endpoint = "https://exploitavoid.com/api"
var leaderboard_id = 15
var leaderboard_secret = "3f2981858c7ff90dd6eaffc4a93589cc"

signal on_received_entries(was_success, entries)
signal on_received_user_entry(was_success, entry)
signal on_sent_user_value(was_success)

var request_entries_http_request
var request_user_entry_http_request
var send_user_value_http_request

func _ready():
	request_entries_http_request = HTTPRequest.new()
	add_child(request_entries_http_request)
	request_entries_http_request.connect("request_completed", self, "_handle_received_entries")
	
	request_user_entry_http_request = HTTPRequest.new()
	add_child(request_user_entry_http_request)
	request_user_entry_http_request.connect("request_completed", self, "_handle_received_user_entry")
	
	send_user_value_http_request = HTTPRequest.new()
	add_child(send_user_value_http_request)
	send_user_value_http_request.connect("request_completed", self, "_handle_sent_user_value")
	
func request_entries(start, count):
	var url = server_endpoint + "/getscoreentries?id={0}&start={1}&count={2}"
	url = url.format([leaderboard_id,start,count])
	request_entries_http_request.request(url)
	
func request_user_entry(name):
	var url = server_endpoint + "/getscoreentries?id={0}&start=1&count=1&search={1}"
	url = url.format([leaderboard_id,name])
	request_user_entry_http_request.request(url)
	
func send_user_value(name, value):
	var url = server_endpoint + "/submitscoreentry"
	var upload_json = "{\"name\":\"{0}\", \"value\":{1}, \"id\":{2}}";
	upload_json = upload_json.format([name, value, leaderboard_id])
	var to_hash = "/submitscoreentry" + upload_json + leaderboard_secret;
	var ctx = HashingContext.new()
	ctx.start(HashingContext.HASH_SHA256)
	ctx.update(to_hash.to_utf8())
	var hash_result = ctx.finish()
	send_user_value_http_request.request(url, PoolStringArray(), true, 2, upload_json + hash_result.hex_encode())
	
func _handle_received_entries(_result, response_code, _headers, body):
	var entries = null
	if response_code == 200:
		entries = parse_json(body.get_string_from_utf8())
	emit_signal("on_received_entries", response_code == 200, entries)

func _handle_received_user_entry(_result, response_code, _headers, body):
	var entry = null
	if response_code == 200:
		entry = parse_json(body.get_string_from_utf8())
	emit_signal("on_received_user_entry", response_code == 200, entry)
	
func _handle_sent_user_value(_result, response_code, _headers, _body):
	emit_signal("on_sent_user_value", response_code == 200)
