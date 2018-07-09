using Newtonsoft.Json;
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Threading.Tasks;

namespace Nx
{
    // Contains layout data.
    // This class should be as close as possible to wire exchange format
    class Layout
    {
        // Layout item
        public class Item
        {
            public string id;
            public int flags;
            public float left;
            public float right;
            public float top;
            public float bottom;
            public float rotation;
            public string resourceId;
            public string resourcePath;
            public float zoomLeft;
            public float zoomRight;
            public float zoomTop;
            public float zoomBottom;
            public string zoomTargetId;
            public string contastParams;
            public string dewarpingParams;
            public bool displayInfo;
        }

        public string id;
        public string parentId;
        public string name;
        public string url;  // should be empty string
        public string typeId;
        public float cellAspectRatio;
        public float horizontalSpacing;
        public float verticalSpacing;
        public List<Item> items;

        public bool locked;
        public int fixedWidth;
        public int fixedHeight;
        public int logicalId;
        public string backgroundImageFilename;
        public int backgroundWidth;
        public int backgroundHeight;
        public float backgroundOpacity;
    }

    class Camera
    {
        public string id;
        public string parentId;
        public string name;
        public string url;
        public string typeId;
        public string mac;
        public string physicalId;
        public bool manuallyAdded;
        public string model;
        public string groupId;
        public string groupName;
        // This status uses literal flags
        public string statusFlags;
        public string vendor;
        public string cameraId;
        public string cameraName;
        public string userDefinedGroupName;
        public bool scheduleEnabled;
        public bool licenseUsed;

        public string motionType;
        public string motionMask;
        // public ScheduleTask scheduleTasks;
        public bool audioEnabled;
        public bool disableDualStreaming;
        public bool controlEnabled;
        public string dewarpingParams;
        public int minArchiveDays;
        public int maxArchiveDays;
        public string preferredServerId;
        public string failoverPriority;
        public string backupType;
        public int logicalId;
        public int recordBeforeMotionSec;
        public int recordAfterMotionSec;
        public string status;
        // public CameraParam addParams;
    }

    // Wraps up a connection to VMS server
    class Connection
    {
        public Connection(string host, int port, string user, string password)
        {
            this.host = host;
            this.port = port;
            client = new HttpClient();
            // This magic is necessary to set authentication:
            var byteArray = Encoding.ASCII.GetBytes(string.Format("{0}:{1}", user, password));
            var header = new AuthenticationHeaderValue("Basic", Convert.ToBase64String(byteArray));
            client.DefaultRequestHeaders.Authorization = header;
        }

        // Makes proper uri
        protected Uri MakeUri(string path, string query)
        {
            return new UriBuilder()
            {
                Port = port,
                Scheme = Uri.UriSchemeHttp,
                Host = host,
                Path = path,
                Query = query,
            }.Uri;
        }

        // Generates an uuid in compatible form. We wrap UUIDs inside {} brackets
        protected string MakeUuid()
        {
            var uuid = System.Guid.NewGuid();
            return "{" + uuid + "}";
        }

        // Get json with all layouts from the server
        // @returns raw json data
        protected async Task<string> GetLayoutsRaw()
        {
            var uri = MakeUri("/ec2/getLayouts", "");
            var response = await client.GetAsync(uri);
            return await response.Content.ReadAsStringAsync();
        }

        // Get json with all layouts from the server
        // @returns raw json data
        protected async Task<string> GetLayoutRaw(string id)
        {
            var uri = MakeUri("/ec2/getLayouts", "id="+id);
            var response = await client.GetAsync(uri);
            return await response.Content.ReadAsStringAsync();
        }

        // Get all layouts from the server
        public async Task<Layout[]> GetLayouts()
        {
            try
            {
                var responseData = await GetLayoutsRaw();
                using (TextReader sr = new StringReader(responseData))
                {
                    var reader = new JsonTextReader(sr);
                    try
                    {
                        return serializer.Deserialize<Layout[]>(reader);
                    }
                    catch(JsonSerializationException ex)
                    {
                        Debug.WriteLine("GetLayouts failed to deserialize response using object array: " + ex.ToString());
                    }

                    // For the case we get a single layout
                    try
                    {
                        var layout = serializer.Deserialize<Layout>(reader);
                        return new Layout[] { layout };
                    }
                    catch(JsonSerializationException ex)
                    {
                        Debug.WriteLine("GetLayouts failed to deserialize response using single object: " + ex.ToString());
                        return null;
                    }
                }
            }
            catch(HttpRequestException ex)
            {
                Debug.WriteLine("GetLayouts failed to send http request: " + ex.ToString());
            }
            return null;
        }

        void GetTileCoords(Layout layout, int tileId, out int x, out int y)
        {
            int w = Math.Max(layout.fixedWidth, 1);
            int h = layout.fixedHeight;
            int left = -(w / 2);
            int top = -(h / 2);
            x = tileId % w;
            y = tileId / w;
        }

        // Get a specific layout
        // @param id: either logical id or full guid of the layout
        public async Task<Layout> GetLayout(string id)
        {
            try
            {
                var responseData = await GetLayoutRaw(id);
                using (TextReader sr = new StringReader(responseData))
                {
                    var reader = new JsonTextReader(sr);
                    try
                    {
                        // We are expecting to get an array with a single element
                        var layouts = serializer.Deserialize<Layout[]>(reader);
                        if (layouts == null || layouts.Length == 0)
                            return null;
                        return layouts[0];
                    }
                    catch (JsonSerializationException ex)
                    {
                        Debug.WriteLine("GetLayout(" + id + ") failed to deserialize response using object array: " + ex.ToString());
                    }
                }
            }
            catch (HttpRequestException ex)
            {
                Debug.WriteLine("GetLayout("+id+") failed to send http request: " + ex.ToString());
            }
            return null;
        }

        // Get a specific camera
        // @returns raw json data
        async Task<string> GetCameraRaw(string id)
        {
            var uri = MakeUri("/ec2/getCameras", String.Format("id={0}", id));
            var response = await client.GetAsync(uri);
            return await response.Content.ReadAsStringAsync();
        }

        // Get a specific camera
        // @param id: either logical id or full guid of the camera
        public async Task<Camera> GetCamera(string id)
        {
            try
            {
                var responseData = await GetCameraRaw(id);
                using (TextReader sr = new StringReader(responseData))
                {
                    var reader = new JsonTextReader(sr);
                    try
                    {
                        var cameras = serializer.Deserialize<Camera[]>(reader);
                        if (cameras == null || cameras.Length == 0)
                            return null;
                        return cameras[0];
                    }
                    catch (JsonSerializationException ex)
                    {
                        Debug.WriteLine("GetCamera("+id+") failed to deserialize camera object: " + ex.ToString());
                    }
                }
            }
            catch (HttpRequestException ex)
            {
                Debug.WriteLine("GetCamera(" + id + ") failed to send http request: " + ex.ToString());
            }
            return null;
        }

        // Get json with all layouts from the server
        // @returns raw json data
        async Task<string> GetCamerasRaw()
        {
            var uri = MakeUri("/ec2/getCameras", "");
            var response = await client.GetAsync(uri);
            return await response.Content.ReadAsStringAsync();
        }

        public async Task<Camera[]> GetCameras()
        {
            try
            {
                var responseData = await GetCamerasRaw();
                using (TextReader sr = new StringReader(responseData))
                {
                    var reader = new JsonTextReader(sr);
                    try
                    {
                        return serializer.Deserialize<Camera[]>(reader);
                    }
                    catch (JsonSerializationException ex)
                    {
                        Debug.WriteLine("GetCameras failed to deserialize response using object array: " + ex.ToString());
                    }

                    // For the case we get a single layout
                    try
                    {
                        var camera = serializer.Deserialize<Camera>(reader);
                        return new Camera[] { camera };
                    }
                    catch (JsonSerializationException ex)
                    {
                        Debug.WriteLine("GetCameras failed to deserialize response using single object: " + ex.ToString());
                        return null;
                    }
                }
            }
            catch (HttpRequestException ex)
            {
                Debug.WriteLine("GetCameras failed to send http request: " + ex.ToString());
            }
            return null;
        }

        public async Task<Layout> AddCameraToLayout(Layout layout, string cameraId, int tileId)
        {
            int tileX = 0;
            int tileY = 0;
            GetTileCoords(layout, tileId, out tileX, out tileY);

            bool contains = false;
            foreach (var item in layout.items)
            {
                // There is already an item in specified location (tileX, tileY)
                if (item.left == tileX && item.top == tileY)
                {
                    Debug.WriteLine("AddCameraToLayout: overriding tile info");

                    item.left = tileX;
                    item.top = tileY;
                    item.right = tileX + 1;
                    item.bottom = tileY + 1;
                    item.flags = 1;
                    item.resourceId = cameraId;
                    item.id = System.Guid.NewGuid().ToString();
                    contains = true;
                    break;
                }
            }

            // Adding new item if it is not already inside
            if (!contains)
            {
                Debug.WriteLine("AddCameraToLayout: adding new item to the layout");
                var item = new Layout.Item()
                {
                    left = tileX,
                    top = tileY,
                    right = tileX + 1,
                    bottom = tileY + 1,
                    flags = 1,
                    resourceId = cameraId,
                    id = MakeUuid()
                };
                layout.items.Add(item);
            }

            // Sync this layout with the server
            await SaveLayout(layout);

            return layout;
        }

        public async Task<Layout> AddCameraToLayout(Layout layout, Camera camera, int tileId)
        {
            return await AddCameraToLayout(layout, camera.id, tileId);
        }

        public async Task<bool> RemoveCameraFromLayout(Layout layout, string cameraId)
        {
            foreach (var item in layout.items)
            {
                // There is already an item in specified location (tileX, tileY)
                if (item.resourceId == cameraId)
                {
                    layout.items.Remove(item);
                    // Sync this layout with the server
                    await SaveLayout(layout);
                    return true;
                }
            }

            return false;
        }

        // Creates a videowall using raw json wallData
        // @param wallData - contains json string with videowall data
        public async Task SaveVideowallRaw(string wallData)
        {
            var uri = MakeUri("/ec2/saveVideowall", "");
            var reqContent = new StringContent(wallData);
            reqContent.Headers.ContentType = new MediaTypeHeaderValue("application/json");
            var response = await client.PostAsync(uri, reqContent);
            Debug.WriteLine("/ec2/saveVideowall got a response: " + response.ToString());
        }

        // Sends /ec2/saveLayout request.
        // @param layoutData - JSON with layout data to be saved
        public async Task SaveLayoutsRaw(string layoutData)
        {
            var uri = MakeUri("/ec2/saveLayout", "");
            var reqContent = new StringContent(layoutData);
            reqContent.Headers.ContentType = new MediaTypeHeaderValue("application/json");
            try
            {
                var response = await client.PostAsync(uri, reqContent);
            }
            catch (HttpRequestException ex)
            {
                Debug.WriteLine("Got an http error during request: " + ex.ToString());
            }
        }

        public async Task SaveLayoutRaw(string layoutData, string id)
        {
            var uri = MakeUri("/ec2/saveLayout", "");
            var reqContent = new StringContent(layoutData);
            reqContent.Headers.ContentType = new MediaTypeHeaderValue("application/json");
            try
            {
                var response = await client.PostAsync(uri, reqContent);
                if (response.StatusCode != System.Net.HttpStatusCode.OK)
                {
                    Debug.WriteLine("SaveLayoutRaw: got http error response: " + response.ToString());
                    Debug.WriteLine("response contents: " + response.Content.ToString());
                }
            }
            catch (HttpRequestException ex)
            {
                Debug.WriteLine("Got an http error during request: " + ex.ToString());
            }
        }

        public async Task SaveLayouts(Layout[] layouts)
        {
            try
            {
                var writer = new StringWriter();
                using (var jsonWriter = new JsonTextWriter(writer))
                {
                    serializer.Serialize(jsonWriter, layouts);
                }

                await SaveVideowallRaw(writer.ToString());
            }
            catch (JsonSerializationException ex)
            {
                Debug.WriteLine("GetCameras failed to deserialize response using object array: " + ex.ToString());
            }
        }

        public async Task SaveLayout(Layout layout)
        {
            try
            {
                var writer = new StringWriter();
                using (var jsonWriter = new JsonTextWriter(writer))
                {
                    serializer.Serialize(jsonWriter, layout);
                }

                await SaveLayoutRaw(writer.ToString(), layout.id);
            }
            catch (JsonSerializationException ex)
            {
                Debug.WriteLine("GetCameras failed to deserialize response using object array: " + ex.ToString());
            }
        }

        private string host;
        private int port;
        private HttpClient client;
        private JsonSerializer serializer = new JsonSerializer();
    }
}
