# Cloud Watch Email Client

## What does the client do?
- Parses the last 30 cloud watch emails for prod.
- Generate the following sql queries for cloud db based on log emails
  - Get user by email
  - Get system by id
  - Get users for a system by id
- Generate aws cli commands for view log errors
  - Current interval is +/- 10 seconds from when the error happened.

## Setting up your environment
### Requirements
- Mac or Linux (currently no support for windows)
- python3
- nodejs

### Building the frontend
Run `./make.sh build_app`.

This will build the frontend and place the dist in server/static

### Creating a client_id.json - TBD
In the meantime ask Nick H for the file.

Place the `client_id.json` file in servers directory.

## Using the client
- Run `./make.sh run_local`.
- Go to http://localhost:5000
