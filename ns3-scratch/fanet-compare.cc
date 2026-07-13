#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/mobility-module.h"
#include "ns3/wifi-module.h"
#include "ns3/aodv-module.h"
#include "ns3/olsr-module.h"
#include "ns3/dsdv-module.h"
#include "ns3/applications-module.h"
#include "ns3/flow-monitor-module.h"
#include <fstream>
#include <iostream>
#include <map>
#include <sstream>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE ("FanetCompare");

uint32_t g_totalLinkBreaks = 0;
std::map<std::pair<uint32_t, uint32_t>, bool> g_linkState;
std::map<std::pair<uint32_t, uint32_t>, double> g_linkEstablishTime;
double g_totalLinkLifetime = 0.0;
uint32_t g_closedLinks = 0;
double g_sumDegree = 0.0;
uint32_t g_topologyChecks = 0;

void CheckTopology (NodeContainer nodes, double rangeThreshold)
{
    uint32_t activeLinks = 0;
    double minD = 9999.0, maxD = 0.0, sumD = 0.0;
    uint32_t pairs = 0;
    uint32_t n = nodes.GetN ();

    for (uint32_t i = 0; i < n; ++i) {
        for (uint32_t j = i + 1; j < n; ++j) {
            Vector p1 = nodes.Get (i)->GetObject<MobilityModel> ()->GetPosition ();
            Vector p2 = nodes.Get (j)->GetObject<MobilityModel> ()->GetPosition ();
            double d = CalculateDistance (p1, p2);
            
            if (d < minD) minD = d;
            if (d > maxD) maxD = d;
            sumD += d;
            pairs++;

            bool isConnected = (d <= rangeThreshold);
            if (isConnected) activeLinks++;

            std::pair<uint32_t, uint32_t> linkPair = std::make_pair (i, j);
            
            if (isConnected) {
                if (g_linkEstablishTime.find(linkPair) == g_linkEstablishTime.end()) {
                    g_linkEstablishTime[linkPair] = Simulator::Now().GetSeconds();
                }
            } else {
                if (g_linkEstablishTime.find(linkPair) != g_linkEstablishTime.end()) {
                    double duration = Simulator::Now().GetSeconds() - g_linkEstablishTime[linkPair];
                    g_totalLinkLifetime += duration;
                    g_closedLinks++;
                    g_linkEstablishTime.erase(linkPair);
                    g_totalLinkBreaks++;
                }
            }
            g_linkState[linkPair] = isConnected;
        }
    }
    
    double currentAvgDegree = (n > 0) ? (2.0 * activeLinks) / n : 0.0;
    g_sumDegree += currentAvgDegree;
    std::cout << "TOPOLOGY_LOG " 
          << Simulator::Now().GetSeconds() << " "
          << currentAvgDegree << std::endl;
    g_topologyChecks++;
    double avgD = (pairs > 0) ? (sumD / pairs) : 0;
    
    std::cout << "Time: " << Simulator::Now ().GetSeconds () << "s | "
              << "Dist(Min/Avg/Max): " << minD << " / " << avgD << " / " << maxD << " m | "
              << "Active Links: " << activeLinks << " / " << pairs 
              << " | Breaks: " << g_totalLinkBreaks << std::endl;

    Simulator::Schedule (Seconds (2.0), &CheckTopology, nodes, rangeThreshold);
}

int main (int argc, char *argv[])
{
    std::string protocol = "AODV";
    std::string mobility = "Realistic"; 
    std::string waypointDir = "waypoints_independent";
    uint32_t nNodes = 5; 
    uint32_t rngRun = 1;
    double totalTime = 32.0;

    CommandLine cmd;
    cmd.AddValue ("protocol", "Routing protocol", protocol);
    cmd.AddValue ("mobility", "Mobility model", mobility);
    cmd.AddValue ("waypointDir", "Directory of waypoint files", waypointDir);
    cmd.AddValue ("nNodes", "Number of UAVs", nNodes);
    cmd.AddValue ("RngRun", "RNG run index", rngRun);
    cmd.Parse (argc, argv);
    
    ns3::RngSeedManager::SetRun (rngRun);

    NodeContainer nodes;
    nodes.Create (nNodes);

    WifiMacHelper wifiMac;
    wifiMac.SetType ("ns3::AdhocWifiMac");

    YansWifiChannelHelper wifiChannel;
    wifiChannel.SetPropagationDelay ("ns3::ConstantSpeedPropagationDelayModel");
    wifiChannel.AddPropagationLoss ("ns3::LogDistancePropagationLossModel",
                                    "Exponent", DoubleValue (3.0),
                                    "ReferenceLoss", DoubleValue (46.67));
    wifiChannel.AddPropagationLoss ("ns3::RangePropagationLossModel",
                                    "MaxRange", DoubleValue (17.5));
    
    YansWifiPhyHelper wifiPhy;
    wifiPhy.SetChannel (wifiChannel.Create ());

    WifiHelper wifi;
    wifi.SetStandard (WIFI_STANDARD_80211a);
    wifi.SetRemoteStationManager ("ns3::ConstantRateWifiManager",
                                  "DataMode", StringValue ("OfdmRate6Mbps"),
                                  "ControlMode", StringValue ("OfdmRate6Mbps"));

    NetDeviceContainer devices = wifi.Install (wifiPhy, wifiMac, nodes);

    InternetStackHelper internet;
    if (protocol == "AODV") {
        AodvHelper aodv;
        internet.SetRoutingHelper (aodv);
    } else if (protocol == "OLSR") {
        OlsrHelper olsr;
        internet.SetRoutingHelper (olsr);
    } else if (protocol == "DSDV") {
        DsdvHelper dsdv;
        internet.SetRoutingHelper (dsdv);
    }
    internet.Install (nodes);

    Ipv4AddressHelper ipv4;
    ipv4.SetBase ("10.1.1.0", "255.255.255.0");
    Ipv4InterfaceContainer interfaces = ipv4.Assign (devices);

    MobilityHelper mobilityHelper;
    if (mobility == "RWP") {
        double areaSize = 50.0 * std::sqrt ((double)nNodes / 5.0);
        std::ostringstream xRange, yRange;
        xRange << "ns3::UniformRandomVariable[Min=0.0|Max=" << areaSize << "]";
        yRange << "ns3::UniformRandomVariable[Min=0.0|Max=" << areaSize << "]";
        
        mobilityHelper.SetPositionAllocator ("ns3::RandomRectanglePositionAllocator",
                                             "X", StringValue (xRange.str()),
                                             "Y", StringValue (yRange.str()));
        
        mobilityHelper.SetMobilityModel ("ns3::RandomWaypointMobilityModel",
                                         "Speed", StringValue ("ns3::UniformRandomVariable[Min=1.0|Max=1.5]"),
                                         "Pause", StringValue ("ns3::ConstantRandomVariable[Constant=0.5]"),
                                         "PositionAllocator", StringValue ("ns3::RandomRectanglePositionAllocator"));
        mobilityHelper.Install (nodes);
    } 
    else if (mobility == "Realistic") {
        for (uint32_t i = 0; i < nodes.GetN (); ++i) {
            Ptr<Node> node = nodes.Get (i);
            Ptr<WaypointMobilityModel> mob = CreateObject<WaypointMobilityModel> ();
            node->AggregateObject (mob);

            uint32_t fileIndex = i % 5;
            double shiftX = (i / 5) * 5.0; 
            double shiftY = (i / 5) * 5.0;

            std::string prefix = waypointDir.empty() ? "" : waypointDir + "/";
            std::string filename = prefix + "waypoints_node" + std::to_string (fileIndex) + ".txt";
            std::ifstream file (filename);
            if (!file.is_open ()) {
                NS_FATAL_ERROR ("Cannot open file: " << filename);
            }

            double time, x, y, z;
            while (file >> time >> x >> y >> z) {
                mob->AddWaypoint (Waypoint (Seconds (time), Vector (x + shiftX, y + shiftY, z)));
            }
            file.close ();
        }
    }

    uint16_t port = 9;
    uint32_t numFlows = nNodes / 2;
    for (uint32_t i = 0; i < numFlows; ++i) {
        uint32_t src = i;
        uint32_t dst = i + numFlows;

        UdpServerHelper server (port + i);
        ApplicationContainer serverApps = server.Install (nodes.Get (dst));
        serverApps.Start (Seconds (5.0));
        serverApps.Stop (Seconds (totalTime));

        UdpClientHelper client (interfaces.GetAddress (dst), port + i);
        client.SetAttribute ("MaxPackets", UintegerValue (10000));
        client.SetAttribute ("Interval", TimeValue (Seconds (0.1)));
        client.SetAttribute ("PacketSize", UintegerValue (1024));
        ApplicationContainer clientApps = client.Install (nodes.Get (src));
        clientApps.Start (Seconds (8.0 + (i * 0.2))); 
        clientApps.Stop (Seconds (totalTime));
    }

    Simulator::Schedule (Seconds (2.0), &CheckTopology, nodes, 17.5);

    FlowMonitorHelper flowmon;
    Ptr<FlowMonitor> monitor = flowmon.InstallAll ();

    Simulator::Stop (Seconds (totalTime + 1.0));
    Simulator::Run ();

    monitor->CheckForLostPackets ();

    std::map<FlowId, FlowMonitor::FlowStats> stats = monitor->GetFlowStats ();

    uint32_t txPackets = 0;
    uint32_t rxPackets = 0;
    double totalDelay = 0.0;
    uint32_t totalForwards = 0;

    for (std::map<FlowId, FlowMonitor::FlowStats>::const_iterator i = stats.begin (); i != stats.end (); ++i) {
        txPackets += i->second.txPackets;
        rxPackets += i->second.rxPackets;
        totalDelay += i->second.delaySum.GetSeconds ();
        totalForwards += i->second.timesForwarded;
    }

    double pdr = (txPackets > 0) ? ((double)rxPackets / txPackets) * 100.0 : 0.0;
    double avgDelay = (rxPackets > 0) ? (totalDelay / rxPackets) * 1000.0 : 0.0;
    double avgHopCount = (rxPackets > 0) ? ((double)totalForwards / rxPackets) + 1.0 : 0.0;

    for (auto const& x : g_linkEstablishTime) {
        g_totalLinkLifetime += (totalTime - x.second);
        g_closedLinks++;
    }
    double avgLinkLifetime = (g_closedLinks > 0) ? (g_totalLinkLifetime / g_closedLinks) : 0.0;
    double overallAvgDegree = (g_topologyChecks > 0) ? (g_sumDegree / g_topologyChecks) : 0.0;

    std::cout << "\n--- FINAL RESULTS ---" << std::endl;
    std::cout << "Protocol: " << protocol << " | Mobility: " << mobility << " | Nodes: " << nNodes << std::endl;
    std::cout << "PDR: " << pdr << " % | Avg Delay: " << avgDelay << " ms" << std::endl;
    std::cout << "Link Breaks: " << g_totalLinkBreaks << " | Avg Hop Count: " << avgHopCount << std::endl;
    std::cout << "Avg Node Degree: " << overallAvgDegree << " | Avg Link Lifetime: " << avgLinkLifetime << "s" << std::endl;
    std::ofstream csvFile;
    csvFile.open ("results.csv", std::ios_base::app);
    csvFile << protocol << "," << mobility << "," << nNodes << "," << pdr << "," << avgDelay << "," 
            << txPackets << "," << rxPackets << "," << g_totalLinkBreaks << "," << avgHopCount << ","
            << overallAvgDegree << "," << avgLinkLifetime << "\n";
    csvFile.close();

    Simulator::Destroy ();
    return 0;
}
