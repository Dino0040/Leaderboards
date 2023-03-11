using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.Serialization;
using System.Runtime.Serialization.Json;
using System.Security.Cryptography;
using System.Text;
using System.Threading.Tasks;
using System.Globalization;
using System.Web;
using UnityEngine;
using UnityEngine.Networking;

public class LeaderboardServerBridge : MonoBehaviour
{
    public string serverEndpoint = "https://exploitavoid.com/leaderboards/v1/api";
    public int leaderboardID = 3;
    public string leaderboardSecret = "656433a96b56132affbfde59758acc44";

    public async Task<List<LeaderboardEntry>> RequestEntries(int start, int count)
    {
        string url = serverEndpoint + $"/get_entries?leaderboard_id={leaderboardID}&start={start}&count={count}";
        string requestResult = await RunUnityWebRequest(UnityWebRequest.Get(url));
        if (requestResult == null) return null;
        List<LeaderboardEntry> scores = DeserializeJson<List<LeaderboardEntry>>(requestResult);
        return scores;
    }

    public async Task<LeaderboardEntry> RequestUserEntry(string name)
    {
        string urlEncodedName = HttpUtility.UrlEncode(name);
        string url = serverEndpoint + $"/get_entries?leaderboard_id={leaderboardID}&start=1&count=1&search={urlEncodedName}";
        string requestResult = await RunUnityWebRequest(UnityWebRequest.Get(url));
        if (requestResult == null) return null;
        List<LeaderboardEntry> scores = DeserializeJson<List<LeaderboardEntry>>(requestResult);
        if (scores != null && scores.Count > 0)
        {
            return scores[0];
        }
        return null;
    }

    public Task<bool> SendUserValue(string name, int value)
    {
        return SendUserValue(name, (IConvertible)value);
    }

    public Task<bool> SendUserValue(string name, float value)
    {
        return SendUserValue(name, (IConvertible)value);
    }

    public Task<bool> SendUserValue(string name, double value)
    {
        return SendUserValue(name, (IConvertible)value);
    }

    async Task<bool> SendUserValue(string name, IConvertible value)
    {
        string url = serverEndpoint + "/update_entry";
        string valueString = value.ToString(CultureInfo.InvariantCulture);
        string uploadJson = SerializeJson(new EntryUpdate(name, valueString, leaderboardID));
        string toHash = "/update_entry" + uploadJson + leaderboardSecret;

        byte[] utfBytes = Encoding.UTF8.GetBytes(toHash);
        byte[] result;
        SHA256 shaM = new SHA256Managed();
        result = shaM.ComputeHash(utfBytes);

        string hashString = BitConverter.ToString(result).Replace("-", "");

        byte[] rawBytes = Encoding.UTF8.GetBytes(uploadJson + hashString);

        DownloadHandlerBuffer d = new DownloadHandlerBuffer();
        UploadHandlerRaw u = new UploadHandlerRaw(rawBytes);
        string requestResult = await RunUnityWebRequest(new UnityWebRequest(url, "POST", d, u));
        return requestResult != null;
    }

    async Task<string> RunUnityWebRequest(UnityWebRequest unityWebRequest)
    {
        using (unityWebRequest)
        {
            await unityWebRequest.SendWebRequestAsync();
            switch (unityWebRequest.result)
            {
                case UnityWebRequest.Result.ConnectionError:
                case UnityWebRequest.Result.DataProcessingError:
                case UnityWebRequest.Result.ProtocolError:
                    Debug.LogError(unityWebRequest.error);
                    Debug.LogError(unityWebRequest.downloadHandler.text);
                    break;
                case UnityWebRequest.Result.Success:
                    return unityWebRequest.downloadHandler.text;
            }
        }
        return null;
    }

    T DeserializeJson<T>(string result)
    {
        DataContractJsonSerializer jsonSer = new DataContractJsonSerializer(typeof(T));
        using (MemoryStream ms = new MemoryStream(Encoding.UTF8.GetBytes(result)){ Position = 0 })
        {
            return (T)jsonSer.ReadObject(ms);
        }
    }

    string SerializeJson<T>(T value)
    {
        DataContractJsonSerializer jsonSer = new DataContractJsonSerializer(typeof(T));
        using (MemoryStream ms = new MemoryStream())
        {
            jsonSer.WriteObject(ms, value);
            ms.Position = 0;
            return new StreamReader(ms).ReadToEnd();
        }
    }
}

public static class WebRequestAsyncExtension
{
    public static Task<AsyncOperation> SendWebRequestAsync(this UnityWebRequest unityWebRequest)
    {
        TaskCompletionSource<AsyncOperation> taskCompletionSource = new TaskCompletionSource<AsyncOperation>();
        unityWebRequest.SendWebRequest().completed += x => taskCompletionSource.SetResult(x);
        return taskCompletionSource.Task;
    }
}

[DataContract]
public class EntryUpdate
{
    [DataMember]
    readonly public string name;
    [DataMember()]
    readonly public string value;
    [DataMember]
    readonly public int leaderboard_id;

    public EntryUpdate(string name, string value, int leaderboard_id)
    {
        this.name = name;
        this.value = value;
        this.leaderboard_id = leaderboard_id;
    }
}

[DataContract]
public class LeaderboardEntry
{
    [DataMember]
    readonly public string name;
    [DataMember(Name = "value")]
    readonly private string _value;
    [DataMember]
    readonly public int position;

    // If you want to parse the value yourself
    // The backend does not support strings as values
    public string GetValueAsString()
    {
        return _value;
    }

    public int GetValueAsInt()
    {
        if(int.TryParse(_value, NumberStyles.Integer, CultureInfo.InvariantCulture, out int result))
        {
            return result;
        }
        else
        {
            return (int)Math.Round(GetValueAsDouble());
        }
    }

    public float GetValueAsFloat()
    {
        return float.Parse(_value, CultureInfo.InvariantCulture);
    }

    public double GetValueAsDouble()
    {
        return double.Parse(_value, CultureInfo.InvariantCulture);
    }
}
