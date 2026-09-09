// The console, from a phone.
//
// Full screen is the point of playing this game and alt-tabbing out of it to
// type a command defeats it - the game loses focus, sometimes the mouse, and
// on a bad day the whole window. A phone on the same network is the way round
// that: the launcher answers on a port, the phone shows the same console, and
// the game is never touched.
//
// Deliberately a TcpListener speaking a few lines of HTTP rather than
// HttpListener. HttpListener wants a URL reservation for anything but
// localhost, which means running as administrator or a netsh command, and
// neither belongs in a game launcher. A socket needs nothing.
//
// It answers on the local network, so it carries a four digit code, shown in
// the console window when the server starts and required on every request.
// That is not security against an attacker on the network; it is enough that a
// stray browser or another device cannot drive the game by accident.

using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Net;
using System.Net.NetworkInformation;
using System.Net.Sockets;
using System.Text;
using System.Threading;

internal sealed class Remote
{
    private readonly Func<string, string[]> _run;
    private readonly Func<int, string[]> _tail;
    private readonly Func<IEnumerable<KeyValuePair<string, string>>> _commands;
    private TcpListener _listener;
    private Thread _thread;
    private volatile bool _stop;

    public string Code { get; private set; }
    public int Port { get; private set; }

    public Remote(Func<string, string[]> run, Func<int, string[]> tail,
                  Func<IEnumerable<KeyValuePair<string, string>>> commands)
    {
        _run = run;
        _tail = tail;
        _commands = commands;
        Code = new Random().Next(1000, 10000).ToString(CultureInfo.InvariantCulture);
    }

    /// The address to type into a phone, or null when nothing could be found.
    public static string LocalAddress()
    {
        try
        {
            // Asking a socket which interface it would use to reach the world
            // gives the address the phone can see, which the host name does not
            // reliably do on a machine with several adapters.
            using (var probe = new Socket(AddressFamily.InterNetwork, SocketType.Dgram, ProtocolType.Udp))
            {
                probe.Connect("8.8.8.8", 65530);
                return ((IPEndPoint)probe.LocalEndPoint).Address.ToString();
            }
        }
        catch (Exception) { return null; }
    }

    /// Every address a phone might reach, best first.
    ///
    /// One address is not enough. This machine has an Ethernet and a Wi-Fi card
    /// on the same network and two virtual switches besides, and the probe above
    /// names only whichever carries the default route - which is not necessarily
    /// the one the phone is on. Virtual adapters and the 169.254 addresses a card
    /// gives itself when nothing answered are dropped, because no phone is ever
    /// on those.
    public static List<string> LocalAddresses()
    {
        var found = new List<string>();
        string best = LocalAddress();
        if (best != null) found.Add(best);
        try
        {
            foreach (NetworkInterface card in NetworkInterface.GetAllNetworkInterfaces())
            {
                if (card.OperationalStatus != OperationalStatus.Up) continue;
                if (card.NetworkInterfaceType == NetworkInterfaceType.Loopback) continue;
                string name = card.Description.ToLowerInvariant();
                if (name.Contains("virtual") || name.Contains("hyper-v")
                    || name.Contains("vethernet") || name.Contains("loopback")) continue;
                foreach (UnicastIPAddressInformation ip in card.GetIPProperties().UnicastAddresses)
                {
                    if (ip.Address.AddressFamily != AddressFamily.InterNetwork) continue;
                    string text = ip.Address.ToString();
                    if (text.StartsWith("169.254") || text.StartsWith("127.")) continue;
                    if (!found.Contains(text)) found.Add(text);
                }
            }
        }
        catch (Exception) { }
        return found;
    }

    public string Start(int firstPort = 8099)
    {
        for (int port = firstPort; port < firstPort + 12; port++)
        {
            try
            {
                _listener = new TcpListener(IPAddress.Any, port);
                _listener.Start();
                Port = port;
                break;
            }
            catch (SocketException) { _listener = null; }
        }
        if (_listener == null) return "no free port between " + firstPort + " and " + (firstPort + 11);

        _stop = false;
        _thread = new Thread(Serve) { IsBackground = true, Name = "SoA remote" };
        _thread.Start();
        return null;
    }

    public void Stop()
    {
        _stop = true;
        try { if (_listener != null) _listener.Stop(); }
        catch (Exception) { }
        _listener = null;
    }

    private void Serve()
    {
        while (!_stop)
        {
            TcpClient client = null;
            try { client = _listener.AcceptTcpClient(); }
            catch (Exception) { return; }          // Stop() closes the listener
            try { Answer(client); }
            catch (Exception) { }
            finally { try { client.Close(); } catch (Exception) { } }
        }
    }

    private void Answer(TcpClient client)
    {
        var stream = client.GetStream();
        client.ReceiveTimeout = 4000;
        var request = new StringBuilder();
        var buffer = new byte[2048];
        while (!request.ToString().Contains("\r\n\r\n"))
        {
            int got = stream.Read(buffer, 0, buffer.Length);
            if (got <= 0) return;
            request.Append(Encoding.UTF8.GetString(buffer, 0, got));
            if (request.Length > 16384) break;
        }
        string line = request.ToString().Split('\n')[0].Trim();
        string[] parts = line.Split(' ');
        if (parts.Length < 2) return;
        string path = parts[1];

        string query = "";
        int mark = path.IndexOf('?');
        if (mark >= 0) { query = path.Substring(mark + 1); path = path.Substring(0, mark); }
        Dictionary<string, string> args = Query(query);

        if (path == "/")
        {
            Send(stream, "text/html; charset=utf-8", Page());
            return;
        }
        string given;
        if (!args.TryGetValue("k", out given) || given != Code)
        {
            Send(stream, "text/plain; charset=utf-8", "wrong code", "403 Forbidden");
            return;
        }
        if (path == "/run")
        {
            string command;
            args.TryGetValue("c", out command);
            string[] said = _run(command ?? "");
            Send(stream, "text/plain; charset=utf-8", string.Join("\n", said));
        }
        else if (path == "/log")
        {
            string from;
            int since = args.TryGetValue("n", out from)
                     && int.TryParse(from, out since) ? since : 0;
            Send(stream, "text/plain; charset=utf-8", string.Join("\n", _tail(since)));
        }
        else
        {
            Send(stream, "text/plain; charset=utf-8", "no", "404 Not Found");
        }
    }

    private static Dictionary<string, string> Query(string query)
    {
        var found = new Dictionary<string, string>();
        foreach (string pair in query.Split('&'))
        {
            if (pair.Length == 0) continue;
            int equals = pair.IndexOf('=');
            string key = equals < 0 ? pair : pair.Substring(0, equals);
            string value = equals < 0 ? "" : Uri.UnescapeDataString(
                pair.Substring(equals + 1).Replace('+', ' '));
            found[key] = value;
        }
        return found;
    }

    private static void Send(Stream stream, string type, string body, string status = "200 OK")
    {
        byte[] content = Encoding.UTF8.GetBytes(body);
        string head = "HTTP/1.1 " + status + "\r\n"
                    + "Content-Type: " + type + "\r\n"
                    + "Content-Length: " + content.Length + "\r\n"
                    + "Cache-Control: no-store\r\n"
                    + "Connection: close\r\n\r\n";
        byte[] header = Encoding.ASCII.GetBytes(head);
        stream.Write(header, 0, header.Length);
        stream.Write(content, 0, content.Length);
        stream.Flush();
    }

    /// The whole page, in one string: no second request, no files to deploy,
    /// and nothing to go missing when the launcher is copied somewhere else.
    private string Page()
    {
        var buttons = new StringBuilder();
        foreach (KeyValuePair<string, string> c in _commands())
        {
            string name = c.Key.TrimEnd('(');
            bool takes = c.Key.EndsWith("(");
            buttons.Append("<button class=q data-c=\"").Append(name)
                   .Append(takes ? "(" : "").Append("\" title=\"")
                   .Append(c.Value.Replace("\"", "&quot;")).Append("\">")
                   .Append(name).Append("</button>");
        }
        return @"<!doctype html><html lang=cs><head>
<meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>
<title>Soldiers of Anarchy</title><style>
:root{color-scheme:dark}
body{margin:0;background:#191b20;color:#e6e8ee;font:15px/1.45 system-ui,sans-serif}
header{padding:10px 14px;background:#23262e;border-bottom:1px solid #33384a}
h1{margin:0;font-size:15px;color:#c8a24a;font-weight:600}
#code{margin:10px 14px;display:flex;gap:8px}
#code input{flex:1;min-width:0}
main{padding:0 14px 14px}
input,button{font:inherit}
input{background:#14161a;color:#e6e8ee;border:1px solid #33384a;border-radius:6px;padding:11px}
button{background:#23262e;color:#e6e8ee;border:1px solid #33384a;border-radius:6px;padding:11px 13px}
button:active{background:#2e3240}
#row{display:flex;gap:8px;margin:10px 0}
#row input{flex:1;min-width:0}
#quick{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px}
#quick button{padding:8px 10px;font-size:13px;color:#8e93a3}
#out{white-space:pre-wrap;font:13px/1.4 ui-monospace,Consolas,monospace;
     background:#14161a;border:1px solid #33384a;border-radius:6px;padding:10px;
     height:52vh;overflow:auto}
.note{color:#8e93a3;font-size:12px;margin:8px 0}
</style></head><body>
<header><h1>Soldiers of Anarchy - console</h1></header>
<div id=code><input id=k inputmode=numeric placeholder='the four digit code'>
<button onclick=save()>OK</button></div>
<main>
<div id=row><input id=c placeholder='a command' autocapitalize=off autocomplete=off
 spellcheck=false onkeydown='if(event.key==""Enter"")run()'>
<button onclick=run()>Send</button></div>
<div id=quick>" + buttons + @"</div>
<div id=out></div>
<div class=note>The code is shown in the console window on the computer.</div>
</main><script>
var k=localStorage.getItem('k')||'';document.getElementById('k').value=k;
var at=0,out=document.getElementById('out');
function save(){k=document.getElementById('k').value.trim();localStorage.setItem('k',k);poll()}
function say(t){if(!t)return;out.textContent+=(out.textContent?'\n':'')+t;out.scrollTop=out.scrollHeight}
function run(){var i=document.getElementById('c'),c=i.value.trim();if(!c)return;
 fetch('/run?k='+encodeURIComponent(k)+'&c='+encodeURIComponent(c))
  .then(function(r){return r.text()}).then(function(t){say(t);at+=t?t.split('\n').length:0});
 i.value='';i.focus()}
document.getElementById('quick').addEventListener('click',function(e){
 var b=e.target.closest('button');if(!b)return;var i=document.getElementById('c');
 i.value=b.dataset.c;i.focus();
 if(!b.dataset.c.endsWith('('))run()});
function poll(){fetch('/log?k='+encodeURIComponent(k)+'&n='+at)
 .then(function(r){return r.text()}).then(function(t){
   if(t){say(t);at+=t.split('\n').length}}).catch(function(){})}
setInterval(poll,1500);poll();
</script></body></html>";
    }
}
