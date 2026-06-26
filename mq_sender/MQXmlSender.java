import com.ibm.mq.*;
import com.ibm.mq.constants.CMQC;
import java.time.LocalDateTime;

/**
 * IBM MQ XML消息发送器
 * 使用IBM官方MQ JAR包发送XML格式消息
 */
public class MQXmlSender {
    
    // MQ连接配置
    private static final String HOST = "localhost";           // MQ主机地址
    private static final int PORT = 1414;                    // MQ端口
    private static final String CHANNEL = "SYSTEM.DEF.SVRCONN"; // 通道名称
    private static final String QMGR = "QM1";                // 队列管理器名称
    private static final String QUEUE_NAME = "DEV.QUEUE.1";  // 目标队列名称
    
    public static void main(String[] args) {
        System.out.println("============================================");
        System.out.println("IBM MQ XML消息发送器");
        System.out.println("============================================");
        System.out.println("目标队列管理器: " + QMGR);
        System.out.println("目标队列: " + QUEUE_NAME);
        System.out.println();
        
        MQQueueManager qmgr = null;
        MQQueue queue = null;
        
        try {
            // 设置MQ连接属性
            MQEnvironment.hostname = HOST;
            MQEnvironment.port = PORT;
            MQEnvironment.channel = CHANNEL;
            MQEnvironment.properties.put(CMQC.TRANSPORT_PROPERTY, CMQC.TRANSPORT_MQSERIES);
            
            // 连接到队列管理器
            System.out.println("🔄 连接到MQ队列管理器: " + QMGR + " (" + HOST + ":" + PORT + ")");
            qmgr = new MQQueueManager(QMGR);
            System.out.println("✅ 连接成功!");
            
            // 打开队列
            int openOptions = CMQC.MQOO_OUTPUT + CMQC.MQOO_FAIL_IF_QUIESCING;
            queue = qmgr.accessQueue(QUEUE_NAME, openOptions);
            System.out.println("📭 已打开队列: " + QUEUE_NAME);
            
            // 构建XML消息体
            String xmlMessage = buildXmlMessage();
            System.out.println("\n📝 准备发送的XML消息:");
            System.out.println("---------------------------------------------------");
            System.out.println(xmlMessage);
            System.out.println("---------------------------------------------------");
            
            // 创建MQ消息
            MQMessage message = new MQMessage();
            message.format = CMQC.MQFMT_STRING;
            message.encoding = CMQC.MQENC_NATIVE;
            message.characterSet = 1208;  // UTF-8
            message.writeString(xmlMessage);
            
            // 设置消息选项
            MQPutMessageOptions pmo = new MQPutMessageOptions();
            pmo.options = CMQC.MQPMO_NO_SYNCPOINT;
            
            // 发送消息
            queue.put(message, pmo);
            System.out.println("\n✅ 消息发送成功!");
            System.out.println("📊 消息长度: " + xmlMessage.getBytes("UTF-8").length + " 字节");
            
        } catch (MQException e) {
            System.err.println("\n❌ MQ异常: " + e.getMessage());
            System.err.println("📋 MQ原因码: " + e.reasonCode);
            System.err.println("💡 可能的原因:");
            System.err.println("   - MQ服务器未启动");
            System.err.println("   - 队列管理器名称不正确");
            System.err.println("   - 队列不存在");
            System.err.println("   - 通道配置错误");
            e.printStackTrace();
        } catch (Exception e) {
            System.err.println("\n❌ 发送消息时发生异常: " + e.getMessage());
            e.printStackTrace();
        } finally {
            // 关闭资源
            try {
                if (queue != null) {
                    queue.close();
                    System.out.println("\n📪 队列已关闭");
                }
                if (qmgr != null) {
                    qmgr.disconnect();
                    System.out.println("🔌 已断开MQ连接");
                }
            } catch (MQException e) {
                e.printStackTrace();
            }
        }
        
        System.out.println("\n============================================");
        System.out.println("发送完成");
        System.out.println("============================================");
    }
    
    /**
     * 构建XML格式消息
     */
    private static String buildXmlMessage() {
        StringBuilder xml = new StringBuilder();
        xml.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n");
        xml.append("<student>\n");
        xml.append("    <id>2024001</id>\n");
        xml.append("    <name>张三</name>\n");
        xml.append("    <age>20</age>\n");
        xml.append("    <className>计算机科学与技术</className>\n");
        xml.append("    <department>信息学院</department>\n");
        xml.append("    <enrollmentDate>2024-09-01</enrollmentDate>\n");
        xml.append("    <status>active</status>\n");
        xml.append("    <metadata>\n");
        xml.append("        <sender>StudentManagementSystem</sender>\n");
        xml.append("        <timestamp>").append(LocalDateTime.now().toString()).append("</timestamp>\n");
        xml.append("        <version>1.0</version>\n");
        xml.append("    </metadata>\n");
        xml.append("</student>");
        return xml.toString();
    }
}
