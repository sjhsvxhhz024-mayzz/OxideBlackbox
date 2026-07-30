package top.niunaijun.blackbox.core.system.api;

import android.os.AsyncTask;
import android.util.Log;

import org.json.JSONObject;
import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import top.niunaijun.blackbox.BlackBoxCore;

public class LicenseVerifier {

    public interface Callback {
        void onResult(boolean isValid, String message);
    }

    public static void verify(final String licenseKey, final Callback callback) {
        new AsyncTask<Void, Void, String>() {
            @Override
            protected String doInBackground(Void... voids) {
                try {
					String packageName = BlackBoxCore.getHostPkg();
                    URL url = new URL("https://blackbox360.business/api/connect.php");
                    HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                    conn.setRequestMethod("POST");
                    conn.setDoOutput(true);
                    conn.setConnectTimeout(10000);
                    conn.setReadTimeout(10000);
					
					String params = "user_key=" + URLEncoder.encode(licenseKey, "UTF-8") + "&package_name=" + URLEncoder.encode(packageName, "UTF-8");
                    //String params = "user_key=" + URLEncoder.encode(licenseKey, "UTF-8");
					
                    OutputStream os = conn.getOutputStream();
                    os.write(params.getBytes());
                    os.flush();
                    os.close();

                    BufferedReader br = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                    String line, response = "";
                    while ((line = br.readLine()) != null) response += line;
                    br.close();

                    return response;
                } catch (Exception e) {
                    return "{\"status\":\"fail\",\"reason\":\"" + e.getMessage() + "\"}";
                }
            }

            @Override
            protected void onPostExecute(String result) {
                Log.d("LICENSE_DEBUG", "Server Response: " + result);
                try {
                    JSONObject json = new JSONObject(result);
                    if (json.getString("status").equals("success")) {
                        callback.onResult(true, "License valid till: " + json.getString("expiry"));
                    } else {
                        callback.onResult(false, json.getString("reason"));
                    }
                } catch (Exception e) {
                    callback.onResult(false, "JSON parsing error: " + e.getMessage());
                }
            }
        }.execute();
    }
}
