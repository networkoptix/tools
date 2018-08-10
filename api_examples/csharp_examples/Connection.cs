using Newtonsoft.Json;
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Net.Http;
using System.Net.Http.Headers;
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
            public string resourceId;
            public string resourcePath;
        }

        public string id;
        public List<Item> items;

        public int fixedWidth;
        public int fixedHeight;
    }

    // Wraps up a connection to VMS server
    class Connection
    {
        public Connection(string host, int port, string user, string password)
        {
            this.host = host;
            this.port = port;

            var credCache = new CredentialCache();
            var sampleUri = MakeUri("", "");
            credCache.Add(sampleUri, "Digest", new NetworkCredential(user, password));

            this.client = new HttpClient( new HttpClientHandler { Credentials = credCache});
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

        // Get json with a specific layout from the server
        // @returns raw json data
        protected async Task<string> GetLayoutRaw(int id)
        {
            var uri = MakeUri("/ec2/getLayouts", "id="+id);
            var response = await client.GetAsync(uri);
            return await response.Content.ReadAsStringAsync();
        }

        void GetTileCoords(Layout layout, int tileId, out int x, out int y)
        {
            int w = Math.Max(layout.fixedWidth, 1);
            int h = layout.fixedHeight;
            int left = -(w / 2);
            int top = -(h / 2);
            x = tileId % w + left;
            y = tileId / w + top;
        }

        // Get a specific layout
        // @param id: layout Logical ID
        public async Task<Layout> GetLayout(int id)
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

        public async Task<Layout> AddCameraToLayout(Layout layout, int cameraId, int tileId)
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
                    item.resourceId = ""; //< Existing id must be cleaned.
                    item.resourcePath = cameraId.ToString();
                    item.id = System.Guid.NewGuid().ToString();
                    contains = true;
                    break;
                }
            }

            // Adding new item if it is not already there.
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
                    resourcePath = cameraId.ToString(),
                    id = System.Guid.NewGuid().ToString()
                };
                layout.items.Add(item);
            }

            // Sync this layout with the server
            await SaveLayout(layout);

            return layout;
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
