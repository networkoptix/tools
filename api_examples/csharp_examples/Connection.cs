using Newtonsoft.Json;
using System;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Threading.Tasks;

namespace Nx
{
    // Wraps up a connection to VMS server
    public class Connection
    {
        public Connection(string host, int port, string user, string password)
        {
            m_host = host;
            m_port = port;

            var credCache = new CredentialCache();
            var sampleUri = makeUri("", "");
            credCache.Add(sampleUri, "Digest", new NetworkCredential(user, password));

            m_client = new HttpClient( new HttpClientHandler { Credentials = credCache});
        }

        // Makes proper uri
        private Uri makeUri(string path, string query)
        {
            return new UriBuilder()
            {
                Port = m_port,
                Scheme = Uri.UriSchemeHttp,
                Host = m_host,
                Path = path,
                Query = query,
            }.Uri;
        }

        public async Task<T> get<T>(string path, string query = "")
        {
            var uri = makeUri(path, query);
            try
            {
                var response = await m_client.GetAsync(uri);
                var responseData = await response.Content.ReadAsStringAsync();
                if (responseData == null)
                    return default(T);
                using (TextReader sr = new StringReader(responseData))
                {
                    var reader = new JsonTextReader(sr);
                    try
                    {
                        return m_serializer.Deserialize<T>(reader);
                    }
                    catch (JsonSerializationException ex)
                    {
                        Debug.WriteLine($"Failed to deserialize response: {ex.ToString()}");
                    }
                }

            }
            catch (HttpRequestException ex)
            {
                Debug.WriteLine($"Failed to get {uri.ToString()}: {ex.ToString()}");
            }
            return default(T);
        }

        public async Task post<T>(T data, string path, string query = "")
        {
            try
            {
                var writer = new StringWriter();
                using (var jsonWriter = new JsonTextWriter(writer))
                {
                    m_serializer.Serialize(jsonWriter, data);
                }

                var reqContent = new StringContent(writer.ToString());
                reqContent.Headers.ContentType = new MediaTypeHeaderValue("application/json");
                try
                {
                    var uri = makeUri(path, query);
                    var response = await m_client.PostAsync(uri, reqContent);
                    if (response.StatusCode != System.Net.HttpStatusCode.OK)
                    {
                        Debug.WriteLine($"Got http error response: {response.ToString()}");
                        Debug.WriteLine($"Response contents: {response.Content.ToString()}");
                    }
                }
                catch (HttpRequestException ex)
                {
                    Debug.WriteLine($"Got an http error during request: {ex.ToString()}");
                }
            }
            catch (JsonSerializationException ex)
            {
                Debug.WriteLine($"Failed to serialize request: {ex.ToString()}");
            }
        }

        private string m_host;
        private int m_port;
        private HttpClient m_client;
        private JsonSerializer m_serializer = new JsonSerializer();
    }
}
