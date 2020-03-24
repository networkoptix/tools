using System;
using System.Diagnostics;
using System.Linq;
using System.Threading.Tasks;

namespace Nx
{
    class examples
    {
        static string host = "localhost";
        static int port = 7001;
        static string login = "admin";
        static string password = "";

        // This example allows to add camera to layout.
        // Camera is specified by its Logical ID.
        // Layout is specified by its Logical ID.
        static async Task layoutExample(string[] args)
        {
            if (args.Length < 3)
            {
                Debug.WriteLine("Usage: examples.exe cameraId layoutId tileId");
                return;
            }
            int cameraId = int.Parse(args[0]);
            int layoutId = int.Parse(args[1]);
            int tileId = int.Parse(args[2]);
            if (cameraId <= 0 || layoutId <= 0)
                return;

            var api = new Nx.Api(new Nx.Connection(host, port, login, password));

            var layout = await api.getLayout(layoutId);
            if (layout is null)
            {
                Debug.WriteLine("No such layout id=" + layoutId);
                return;
            }
            await api.addCameraToLayout(layout, cameraId, tileId);
            Debug.WriteLine("Done");
        }

        static async Task usersExample()
        {
            var api = new Nx.Api(new Nx.Connection(host, port, login, password));
            var userList = await api.getUsers();
            foreach (var user in userList)
            {
                Debug.WriteLine($"User {user.name} found. It's full name is {user.fullName}");
                if (user.fullName.Length == 0)
                {
                    user.fullName = char.ToUpper(user.name[0]) + user.name.Substring(1);
                    Debug.WriteLine($"Fill {user.name} full name with {user.fullName}");
                    await api.saveUser(user);
                }
            }

            var testUser = userList.FirstOrDefault(user => user.name == "test");
            if (testUser != null)
            {
                Debug.WriteLine("Deleting test user");
                await api.deleteUser(testUser);
            }
            else
            {
                Debug.WriteLine("Creating test user with live viewer permissions");
                User test = new User
                {
                    name = "test",
                    fullName = "User For Testing",
                    permissions = "GlobalAccessAllMediaPermission",
                    realm = "VMS"
                };
                test.setPassword("testPassword123");
                await api.saveUser(test);
            }

            Debug.WriteLine("Done");
        }

        static void Main(string[] args)
        {
            //LayoutExample(args).GetAwaiter().GetResult();
            usersExample().Wait();
        }
    }
}
