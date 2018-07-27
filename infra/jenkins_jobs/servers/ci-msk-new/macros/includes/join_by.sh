# https://stackoverflow.com/questions/1527049/join-elements-of-an-array
function join_by {
	local d=$1
	shift
	echo -n "$1"
	shift
	printf "%s" "${@/#/$d}"
}
