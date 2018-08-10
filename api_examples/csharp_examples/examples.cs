using System.Diagnostics;
using System.Threading.Tasks;

namespace Nx
{
    class examples
    {
        static string server = "localhost";
        static int port = 7001;
        static string user = "admin";
        static string password = "";

        // This example allows to add camera to layout.
        // Camera is specified by its Logical ID.
        // Layout is specified by its Logical ID.
        static async Task LayoutExample(string[] args)
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

            var api = new Nx.Connection(server, port, user, password);

            var layout = await api.GetLayout(layoutId);
            if (layout is null)
            {
                Debug.WriteLine("No such layout id=" + layoutId);
                return;
            }
            await api.AddCameraToLayout(layout, cameraId, tileId);
            Debug.WriteLine("Done");
        }

        static void Main(string[] args)
        {
            LayoutExample(args).GetAwaiter().GetResult();
        }
    }
}
