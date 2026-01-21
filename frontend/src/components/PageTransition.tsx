import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/router";
import React, { ReactNode } from "react";

interface PageTransitionProps {
  children: ReactNode;
}

export default function PageTransition({ children }: PageTransitionProps) {
  const router = useRouter();

  // Variants for different page animations
  const pageVariants = {
    initial: {
      opacity: 0,
      y: 20,
    },
    animate: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.5,
        ease: "easeOut",
      },
    },
    exit: {
      opacity: 0,
      y: -20,
      transition: {
        duration: 0.3,
        ease: "easeIn",
      },
    },
  };

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={router.route}
        initial="initial"
        animate="animate"
        exit="exit"
        variants={pageVariants}
        style={{ width: "100%" }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}
