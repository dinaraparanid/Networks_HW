import java.io.{BufferedReader, InputStreamReader}
import scala.annotation.targetName
import scala.util.Using

private val MaskPartLen = 8
private val MaskLen = MaskPartLen * 4

extension (ipInt: Int)
  private def toIpString =
    f"${ipInt >> 24}.${(ipInt & 0xFFFFFF) >> 16}.${(ipInt & 0xFFFF) >> 8}.${ipInt & 0xFF}"

extension (ip: String)
  private def nums: List[Int] =
    ip.split("\\.").map(_.toInt).toList

  private def toBinary: String =
    def fillToIpPart(part: String): String =
      "0".repeat(MaskPartLen - part.length) + part

    def partToBinary(part: Int): String =
      fillToIpPart(Integer.toString(part, 2))

    ip.nums map partToBinary mkString ""

  private def combined: Int =
    Integer.parseInt(ip.toBinary, 2)

  @targetName("binAnd")
  def #&#(other: String): String =
    (ip.nums zip other.nums)
      .map(_ & _)
      .map(_.toString)
      .mkString(".")

  @targetName("binOr")
  def #|# (other: String): String =
    (ip.nums zip other.nums)
      .map(_ | _)
      .map(_.toString)
      .mkString(".")

  def binInc: String =
    (ip.combined + 1).toIpString

  def binDec: String =
    (ip.combined - 1).toIpString

extension (rawIp: String)
  def toIpFormat: String =
    rawIp
      .grouped(8)
      .map(Integer.parseInt(_, 2))
      .mkString(".")

private def subnetMask(port: Int): String =
  ("1".repeat(port) + "0".repeat(MaskLen - port)).toIpFormat

private def wildcard(port: Int): String =
  ("0".repeat(port) + "1".repeat(MaskLen - port)).toIpFormat

private def networkAddress(ip: String, subnetMask: String): String =
  ip #&# subnetMask

private def broadcastAddress(ip: String, wildcard: String): String =
  ip #|# wildcard

private def minHostAddress(networkAddress: String): String =
  networkAddress.binInc

private def maxHostAddress(ip: String): String =
  ip.binDec

private def numberOfHosts(port: Int): Int =
  (BigInt(2).pow(MaskLen - port) - 2).toInt

@main
def main(): Unit =
  Using(BufferedReader(InputStreamReader(System.in))): reader ⇒
    val List(ip, portStr) = reader.readLine().split("/").toList
    val port = portStr.toInt
    val subnet = subnetMask(port)
    val wldcrd = wildcard(port)
    val netAddr = networkAddress(ip, subnet)
    val brdcstAddr = broadcastAddress(ip, wldcrd)
    val minHstAddr = minHostAddress(netAddr)
    val maxHstAddr = maxHostAddress(brdcstAddr)
    val hostsNum = numberOfHosts(port)

    println(f"Subnet mask: $subnet")
    println(f"Wildcard: $wldcrd")
    println(f"Network address: $netAddr")
    println(f"Broadcast address: $brdcstAddr")
    println(f"Min Host address: $minHstAddr")
    println(f"Max Host address: $maxHstAddr")
    println(f"Number of hosts: $hostsNum")
