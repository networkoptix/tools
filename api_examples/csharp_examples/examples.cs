using System;
using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Threading.Tasks;

namespace Nx
{
    class examples
    {
        static string server = "localhost";
        static int port = 7001;
        static string user = "admin";
        static string password = "";

        // This example creates a videowall using predefined json data
        static async Task VideowallExample(string[] args)
        {
            if (args.Length < 2)
            {
                Debug.WriteLine("Usage: examples.exe wall");
                return;
            }

            var api = new Nx.Connection(server, port, "admin", "qweasd123");
            // Supposing that wallData.json file is nearby.
            var videoWallData = File.ReadAllText("wallData.json");
            var task = api.SaveVideowallRaw(videoWallData);
            task.Wait();
            Debug.WriteLine("Done");
        }

        // This example allows to add camera to layout
        // Camera is specified by its id
        // Layout is specified by its id
        static async Task LayoutExample(string[] args)
        {
            if (args.Length < 4)
            {
                Debug.WriteLine("Usage: examples.exe cameraId layoutId tileId");
                return;
            }

            var api = new Nx.Connection(server, port, "admin", "qweasd123");

            // This IDs can be logical ids or guids
            string cameraId = args[1];
            string layoutId = args[2];
            int tileId = 0;

            var layouts = await api.GetLayouts();
            var cameras = await api.GetCameras();

            int tmp = 0;
            if (int.TryParse(cameraId, out tmp))
            {
                Debug.WriteLine("Using logicalId=" + tmp + " for the camera");
            }

            if(int.TryParse(layoutId, out tmp))
            {
                Debug.WriteLine("Using logicalId=" + tmp + " for the layout");
            }

            if (!int.TryParse(args[3], out tileId))
            {
                Debug.WriteLine("Wrong tile format");
                return;
            }

            var camera = await api.GetCamera(cameraId);
            if (camera is null)
            {
                Debug.WriteLine("No such camera id=" + cameraId);
                return;
            }
            else
            {
                Debug.WriteLine("Found camera id=" + camera.id);
            }

            var layout = await api.GetLayout(layoutId);
            if (layout is null)
            {
                Debug.WriteLine("No such layout id=" + layoutId);
                return;
            }
            else
            {
                Debug.WriteLine("Found layout id=" + layout.id);
            }

            layout = await api.AddCameraToLayout(layout, camera, tileId);

            Debug.WriteLine("Done");
        }

        static void Main(string[] args)
        {
            if (args.Length < 1)
            {
                Debug.WriteLine("Command was not specified.\nUsage: example.exe command={layout|wall} ...");
            }
            else if (args[0] == "layout")
                LayoutExample(args).GetAwaiter().GetResult();
            else if (args[0] == "wall")
                VideowallExample(args);
        }
    }
}
