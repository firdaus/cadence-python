import py4j.GatewayServer;

public class JavaGateway {

    public static void main(String[] args) {
        GatewayServer gatewayServer = new GatewayServer();
        gatewayServer.start();
        System.out.println("Gateway Server Started");
    }
}
