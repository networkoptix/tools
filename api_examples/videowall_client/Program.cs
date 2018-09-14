using Newtonsoft.Json;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using Newtonsoft.Json.Linq;
using WebSocketSharp;

namespace Nx
{
    class videowall_client
    {
        static string host = "localhost";
        static int port = 7001;
        static string videoWallId = "{c9a802fc-aa33-4afb-8701-a3943e8153ba}";
        static string screenId = "{3b25cc0a-8a7c-458c-adc8-8e173a9b8d7f}";
        static string runtimeId = "{368ee6da-7608-45a4-9867-5a0af04c7e8d}";

        private Thread m_transactionsThread;

        // Makes proper uri
        private Uri MakeUri(string path, string query, string scheme)
        {
            return new UriBuilder()
            {
                Port = port,
                Scheme = scheme,
                Host = host,
                Path = path,
                Query = query,
            }.Uri;
        }

        private class ControlMessage
        {
            public int operation;
            public string videowallGuid;
            public string instanceGuid;

            [JsonProperty(PropertyName="params")]
            public Dictionary<string, string> parameters;
        }

        private JToken readTransaction(string content)
        {
            return JObject.Parse(content)["tran"];
        }

        private void handleMessage(object sender, MessageEventArgs e)
        {
            string content = "";
            if (e.IsText)
                content = e.Data;
            else if (e.IsBinary)
                content = System.Text.Encoding.UTF8.GetString(e.RawData);

            var transaction = readTransaction(content);
            if (transaction == null)
                return;

            string command = transaction["command"].ToString();
            Console.WriteLine($"Got command {command}");

            if (command == "videowallControl")
            {
                var controlMessage = transaction["params"].ToObject<ControlMessage>();
                string parameters = string.Join("\n",
                    controlMessage.parameters.Select((key, value) => $"{key}: {value}"));

                Console.WriteLine($"Parsed control message operation {controlMessage.operation}" +
                              $"sent to {controlMessage.videowallGuid}, {controlMessage.instanceGuid}" +
                              $"with params {parameters}");
            }
        }

        private void startReceivingNotifications(CancellationToken cancellation)
        {
            m_transactionsThread = new Thread(() =>
            {
                var eventsUri = MakeUri("ec2/messageBus",
                    "format=json" +
                    "&peerType=PT_VideowallClient" +    //< Must be here
                    $"&runtime-guid={runtimeId}" +
                    $"&videoWallInstanceGuid={screenId}",
                    "ws");
                var headers = new Dictionary<string, string>()
                {
                    {"X-NetworkOptix-VideoWall", videoWallId},
                    {"X-runtime-guid", runtimeId}
                };

                using (var ws = new WebSocketSharp.WebSocket (eventsUri.ToString()))
                {
                    ws.SetCredentials(videoWallId, "", true);
                    ws.CustomHeaders = headers;
                    ws.OnMessage += handleMessage;
                    ws.Connect();

                    while (!cancellation.IsCancellationRequested)
                    {
                        Thread.Sleep(200);
                    }
                }
            });
            m_transactionsThread.Start();
        }

        private void stopReceivingNotificaitions()
        {
            m_transactionsThread.Join();
        }

        static void Main(string[] args)
        {
            CancellationTokenSource source = new CancellationTokenSource();
            Console.CancelKeyPress += (_, __) => source.Cancel();
            CancellationToken token = source.Token;

            Console.WriteLine("Press any key to stop the client.");

            var client = new videowall_client();
            client.startReceivingNotifications(token);
            Console.ReadKey();
            Console.WriteLine("Please wait while connection is closing...");
            source.Cancel();
            client.stopReceivingNotificaitions();
            source.Dispose();
        }
    }
}
