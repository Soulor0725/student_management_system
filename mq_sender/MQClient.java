import com.ibm.mq.MQQueueManager;
import com.ibm.mq.MQQueue;
import com.ibm.mq.MQMessage;
import com.ibm.mq.constants.CMQC;

public class MQClient {
    public static void main(String[] args) throws Exception {
        // MQ配置
        String host = "10.43.72.8";
        int port = 1424;
        String channel = "UPP";
        String qmgr = "QMUMBF8";
        String queue = "DEV.QUEUE.1";
        String user = "mqm";
        String pass = "mqm";
        
        // 设置环境
        com.ibm.mq.MQEnvironment.hostname = host;
        com.ibm.mq.MQEnvironment.port = port;
        com.ibm.mq.MQEnvironment.channel = channel;
        com.ibm.mq.MQEnvironment.userID = user;
        com.ibm.mq.MQEnvironment.password = pass;
        com.ibm.mq.MQEnvironment.properties.put(CMQC.TRANSPORT_PROPERTY, CMQC.TRANSPORT_MQSERIES);
        
        // 连接发送
        MQQueueManager q = new MQQueueManager(qmgr);
        MQQueue qq = q.accessQueue(queue, CMQC.MQOO_OUTPUT);
        MQMessage msg = new MQMessage();
        msg.writeString("Hello IBM MQ!");
        qq.put(msg);
        
        System.out.println("发送成功");
        
        qq.close();
        q.disconnect();
    }
}
