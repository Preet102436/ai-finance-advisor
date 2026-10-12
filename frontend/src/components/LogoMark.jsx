import logoIcon from "../assets/logo-icon.png";

export default function LogoMark({ size = 26 }) {
  return (
    <img
      src={logoIcon}
      width={size}
      height={size}
      alt=""
      aria-hidden="true"
      style={{ display: "block", objectFit: "contain" }}
    />
  );
}
