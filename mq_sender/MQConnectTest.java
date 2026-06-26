import com.ibm.mq.MQQueueManager;
import com.ibm.mq.constants.CMQC;

public class MQConnectTest {
    public static void main(String[] args) throws Exception {
        // MQ配置
        String host = "10.43.72.8";
        int port = 1424;
        String channel = "DC.SVRCONN";
        String qmgr = "QMUMBF8";
        String user = "UPP";
        String pass = "mqm";
        
        // 设置MQ环境
        com.ibm.mq.MQEnvironment.hostname = host;
        com.ibm.mq.MQEnvironment.port = port;
        com.ibm.mq.MQEnvironment.channel = channel;
        com.ibm.mq.MQEnvironment.userID = user;
        com.ibm.mq.MQEnvironment.password = pass;
        com.ibm.mq.MQEnvironment.properties.put(CMQC.TRANSPORT_PROPERTY, CMQC.TRANSPORT_MQSERIES);
        
        // 连接MQ
        MQQueueManager q = new MQQueueManager(qmgr);
        System.out.println("连接成功: " + q.getName());
        q.disconnect();
    }
}
