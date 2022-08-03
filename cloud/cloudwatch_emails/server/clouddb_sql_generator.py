import argparse

ACCOUNT_BY_EMAIL = "select * from account where email=\"{email}\";"
LIST_SYSTEM_INFO = "select * from system where id=\"{system_id}\";"
LIST_SYSTEMS_USERS = "select a.email, sta.access_role_id, sta.user_role_id, sta.is_enabled from account as a inner join system_to_account as sta on a.id=sta.account_id where sta.system_id=\"{system_id}\";"
LIST_USERS_SYSTEMS = "select s.name, s.id, s.status_code, s.customization from system_to_account as sta inner join system as s on s.id=sta.system_id where sta.account_id=\"{account_id}\";"

def generate_sql(email="", account_id="", system_id=""):
	output = ""
	if email:
		output += ACCOUNT_BY_EMAIL.replace("{email}", email) + "\n"

	if account_id:
		output += LIST_USERS_SYSTEMS.replace("{account_id}", account_id) + "\n"

	if system_id:
		output += LIST_SYSTEM_INFO.replace("{system_id}", system_id) + "\n"
		output += LIST_SYSTEMS_USERS.replace("{system_id}", system_id) + "\n"

	return output


def get_cmd_args():
	parser = argparse.ArgumentParser("clouddb_sql_generator")
	parser.add_argument("-e", "--email",  nargs="?", help="Account email", default="")
	parser.add_argument("-ai", "--account_id", nargs="?", help="Account Id", default="")
	parser.add_argument("-si", "--system_id", nargs="?", help="System Id", default="")
	return parser.parse_args()


def main():
	args = get_cmd_args()
	return generate_sql(email=args.email, account_id=args.account_id, system_id=args.system_id)


if __name__ == "__main__":
	print(f"QUERIES:\n{main()}")