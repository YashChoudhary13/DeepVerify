import { motion } from "framer-motion";
import Link from "next/link";
import { useRouter } from "next/router";
import React, { ReactNode } from "react";

interface AnimatedLinkProps {
  href: string;
  children: ReactNode;
  className?: string;
}

export default function AnimatedLink({ href, children, className }: AnimatedLinkProps) {
  const router = useRouter();
  const isActive = router.pathname === href;

  return (
    <Link href={href}>
      <motion.a
        className={className}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.98 }}
        animate={isActive ? { color: "#3b82f6" } : { color: "inherit" }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
      >
        {children}
      </motion.a>
    </Link>
  );
}
