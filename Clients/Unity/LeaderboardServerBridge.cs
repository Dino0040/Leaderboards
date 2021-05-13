using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.Serialization;
using System.Runtime.Serialization.Json;
using System.Security.Cryptography;
using System.Text;
using System.Threading.Tasks;
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
        using (UnityWebRequest unityWebRequest = UnityWebRequest.Get(url))
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
                    List<LeaderboardEntry> scores = DeserializeJson<List<LeaderboardEntry>>(unityWebRequest.downloadHandler.text);
                    return scores;
            }
        }
        return null;
    }

    public async Task<LeaderboardEntry> RequestUserEntry(string name)
    {
        string url = serverEndpoint + $"/get_entries?leaderboard_id={leaderboardID}&start=1&count=1&search={name}";
        using (UnityWebRequest unityWebRequest = UnityWebRequest.Get(url))
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
                    List<LeaderboardEntry> scores = DeserializeJson<List<LeaderboardEntry>>(unityWebRequest.downloadHandler.text);
                    if (scores != null && scores.Count > 0)
                    {
                        return scores[0];
                    }
                    return null;
            }
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
        string valueString = value.ToString();
        string uploadJson = $"{{\"name\":\"{name}\", \"value\":{valueString}, \"leaderboard_id\":{leaderboardID}}}";
        string toHash = "/update_entry" + uploadJson + leaderboardSecret;

        byte[] utfBytes = Encoding.UTF8.GetBytes(toHash);
        byte[] result;
        SHA256 shaM = new SHA256Managed();
        result = shaM.ComputeHash(utfBytes);

        string hashString = BitConverter.ToString(result).Replace("-", "");

        byte[] rawBytes = Encoding.ASCII.GetBytes(uploadJson + hashString);

        DownloadHandlerBuffer d = new DownloadHandlerBuffer();
        UploadHandlerRaw u = new UploadHandlerRaw(rawBytes);
        using (UnityWebRequest unityWebRequest = new UnityWebRequest(url, "POST", d, u))
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
                    return true;
            }
        }
        return false;
    }

    T DeserializeJson<T>(string result)
    {
        DataContractJsonSerializer jsonSer = new DataContractJsonSerializer(typeof(T));
        using MemoryStream ms = new MemoryStream(Encoding.UTF8.GetBytes(result))
        {
            Position = 0
        };
        return (T)jsonSer.ReadObject(ms);
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
        if(int.TryParse(_value, out int result))
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
        return float.Parse(_value);
    }

    public double GetValueAsDouble()
    {
        return double.Parse(_value);
    }
}
