import datetime
import re
import sys

from .clouddb_sql_generator import generate_sql


log_event_pattern = re.compile(r"\[(?:WARNING|ERROR|CRITICAL)\].+")
ignore_routes_pattern = re.compile(f"/api/(?:account(?:/activate|/register|/check)?|systems)$")
link_pattern = re.compile(r"<a.*href=(?:3D)?\"(.+\/cloudwatch\/[^ ]+)\">", re.S|re.M)
group_pattern = re.compile(r"group=(.*);stream")
date_pattern = re.compile(r"(\d\d\d\d-\d\d\-\d\d \d\d:\d\d:\d\d)")
time_interval_seconds = 10

email_pattern = re.compile(r"(?:'email': '|User: )([^\s']+)")
system_id_pattern = re.compile(r"http://[^\s]+/([\w\d]{8}-(?:[\w\d]{4}-){3}[\w\d]{12})")


def extract_base_url(body):
	email_links = link_pattern.findall(body)
	if len(email_links) == 0:
		print(body)
		raise Exception("Cannot find link to logger!")
	return email_links[0]

def extract_log_group(link):
	group_search = group_pattern.search(link)
	if len(group_search.groups()) == 0:
		raise Exception("Cannot find log group")
	return group_search.groups(0)[0]


def process_email(body):
	global time_interval_seconds
	try:
		link = extract_base_url(body)
		group = extract_log_group(link)
	except Exception as e:
		# print(e)
		# print(body)
		return None
	messages = log_event_pattern.findall(body)
	alarms = []
	for message in messages:
		message = message.replace(r"&#39;", "\'").replace(r"&#34;", "\"")
		parsed_date = date_pattern.search(message)
		if not parsed_date or ignore_routes_pattern.search(message):
			continue

		date = parsed_date.group().replace(" ", "T")
		time = datetime.datetime.fromisoformat(date)
		start = f"{(time - datetime.timedelta(seconds=time_interval_seconds)).isoformat()}Z"
		end = f"{(time + datetime.timedelta(seconds=time_interval_seconds)).isoformat()}Z"
		alarms.append({
			"cmd": f"awslogs get {group} --start={start} --end={end}",
			"reason": message,
		})

	return {
		"emails": [f"{generate_sql(email=email)}" for email in set(email_pattern.findall(body)) if 'not' not in email],
		"system_ids": [f"{generate_sql(system_id=system_id)}" for system_id in set(system_id_pattern.findall(body))],
		"alarms": alarms
	}



def main():
	file_path = sys.argv[1]
	with open(file_path, 'r') as f:
		email = f.read()
		process_email(email)


if __name__ == "__main__":
	main()
